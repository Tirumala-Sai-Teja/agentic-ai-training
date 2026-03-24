"""
run_langgraph.py  ── Cease & Desist Document Processing System
──────────────────────────────────────────────────────────────
Framework : LangChain + LangGraph + Groq

Features:
  ✅ LLM-based PDF extraction       (Groq vision, no PdfReader)
  ✅ Confidence-scored classification (llama-3.3-70b, all classes)
  ✅ Confidence routing             (>99% auto, <=99% → HITL for ALL classes)
  ✅ Memory / duplicate detection   (audit log)
  ✅ HITL via web API               (no blocking input() call)
  ✅ Folder batch processing
  ✅ Full audit trail               (JSONL)
  ✅ Arize Phoenix tracing          (ONE trace per document, nested spans)

Routing logic:
  confidence > 95%   → auto-route as cease OR irrelevant
  confidence <= 95%  → ALWAYS goes to HITL (cease, irrelevant, uncertain)

Tracing design:
  process_document()          ← root span
    ├── memory_check_agent    ← child span
    ├── document_loader_agent ← child span
    ├── classification_agent  ← child span
    ├── database/archiving    ← child span
    └── audit_agent           ← child span

Usage (CLI):
  python run_langgraph.py sample_docs/         ← whole folder
  python run_langgraph.py sample_docs/doc.pdf  ← single file

Tracing:
  Start Phoenix:  python -m phoenix.server.main &
  Open UI:        http://localhost:6006
"""

import sys
import os
import base64
import json
import sqlite3
import operator
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from typing import TypedDict, Optional, List, Annotated

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "lg_impl", ".env"))
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver


# ═══════════════════════════════════════════════════════════
# 1.  ARIZE PHOENIX TRACING
# ═══════════════════════════════════════════════════════════

def _setup_tracing():
    """
    Initialise Arize Phoenix tracing with OpenTelemetry.

    Key design: process_document() opens the root span.
    All agent spans created inside app.invoke() are automatically
    children because invoke() runs synchronously on the same thread,
    so OpenTelemetry's thread-local context propagates naturally.

    Result in Phoenix: ONE trace per document with child spans.
    """
    try:
        from phoenix.otel import register
        from opentelemetry import trace

        register(
            project_name="cease-desist-processor",
            auto_instrument=True,
        )
        tracer = trace.get_tracer("cease_desist_pipeline")
        print("✅ [Tracing] Arize Phoenix active → http://localhost:6006")
        return tracer
    except ImportError:
        print("⚠️  [Tracing] Phoenix not installed — run: pip install arize-phoenix-otel")
        return None
    except Exception as e:
        print(f"⚠️  [Tracing] Phoenix init failed: {e}")
        return None


tracer = _setup_tracing()


def _span(name: str):
    """Return a real OTel span or a no-op context manager."""
    if tracer:
        return tracer.start_as_current_span(name)
    return nullcontext()


def _set_attrs(span, **kwargs):
    """Safely set attributes on a span — silently does nothing if tracing is off."""
    if span is None or tracer is None:
        return
    try:
        for k, v in kwargs.items():
            span.set_attribute(
                k,
                str(v) if not isinstance(v, (bool, int, float, str)) else v
            )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
# 2.  MODELS
# ═══════════════════════════════════════════════════════════

GROQ_API_KEY         = os.getenv("GROQ_API_KEY")
VISION_MODEL         = "meta-llama/llama-4-scout-17b-16e-instruct"
TEXT_MODEL           = "llama-3.3-70b-versatile"

# ── Confidence threshold ───────────────────────────────────
# Only auto-route when confidence is ABOVE this value.
# Any document (cease OR irrelevant) with confidence <= this
# threshold is sent to HITL for human review.
CONFIDENCE_THRESHOLD = 95

vision_llm = ChatGroq(api_key=GROQ_API_KEY, model=VISION_MODEL)
llm        = ChatGroq(api_key=GROQ_API_KEY, model=TEXT_MODEL)


# ═══════════════════════════════════════════════════════════
# 3.  SHARED STATE
# ═══════════════════════════════════════════════════════════

class AgentState(TypedDict):
    pdf_path:               str
    document_text:          str
    document_name:          str
    classification:         Optional[str]   # "cease"|"irrelevant"|"hitl_needed"
    classification_reason:  str
    confidence_score:       int             # 0–100 for ALL classification types
    irrelevant_reason:      str
    extracted_details:      dict
    human_decision:         Optional[str]
    action_taken:           str
    duplicate_detected:     bool
    audit_log:              Annotated[List[dict], operator.add]


# ═══════════════════════════════════════════════════════════
# 4.  STORAGE CONSTANTS & DB INIT
# ═══════════════════════════════════════════════════════════

DB_PATH      = "cease_desist.db"
ARCHIVE_FILE = "irrelevant_documents.txt"
AUDIT_FILE   = "audit_log.jsonl"


def _init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cease_requests (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            received_date   TEXT,
            document_name   TEXT,
            sender_name     TEXT,
            sender_address  TEXT,
            cease_activity  TEXT,
            confidence      INTEGER,
            raw_text        TEXT,
            created_at      TEXT
        )
    """)
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════
# 5.  TOOLS
# ═══════════════════════════════════════════════════════════

@tool
def store_cease_request(
    received_date: str, document_name: str, sender_name: str,
    sender_address: str, cease_activity: str, confidence: int, raw_text: str,
) -> str:
    """Store a valid cease & desist request in SQLite."""
    _init_db()
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        conn.execute(
            """INSERT INTO cease_requests
               (received_date, document_name, sender_name, sender_address,
                cease_activity, confidence, raw_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (received_date, document_name, sender_name, sender_address,
             cease_activity, confidence, raw_text[:2000], datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()
    return f"Stored cease request for '{document_name}' (confidence: {confidence}%)."


@tool
def archive_irrelevant_document(
    received_date: str, document_name: str, reason: str, confidence: int,
) -> str:
    """Archive an irrelevant document with reason and confidence to flat file."""
    with open(ARCHIVE_FILE, "a") as f:
        f.write(
            f"{received_date} | {document_name} | "
            f"confidence: {confidence}% | reason: {reason}\n"
        )
    return f"Archived '{document_name}' as irrelevant (confidence: {confidence}%)."


@tool
def write_audit_entry(
    document_name: str, classification: str, reason: str,
    confidence: int, action: str, reviewed_by: str = "system",
) -> str:
    """Write a compliance audit log entry to JSONL."""
    entry = {
        "timestamp":      datetime.now().isoformat(),
        "document_name":  document_name,
        "classification": classification,
        "confidence":     confidence,
        "reason":         reason,
        "action":         action,
        "reviewed_by":    reviewed_by,
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return f"Audit entry written for '{document_name}' (confidence: {confidence}%)."


# ═══════════════════════════════════════════════════════════
# 6.  PDF EXTRACTION  (Groq vision — no PdfReader)
# ═══════════════════════════════════════════════════════════

def _page_to_base64_png(page) -> str:
    pix = page.get_pixmap(dpi=150)
    return base64.standard_b64encode(pix.tobytes("png")).decode("utf-8")


def _llm_extract_pdf(pdf_path: str) -> str:
    """Render each PDF page to PNG and extract text via Groq vision."""
    try:
        import fitz
    except ImportError:
        raise ImportError("Install PyMuPDF:  pip install pymupdf")

    doc       = fitz.open(pdf_path)
    num_pages = len(doc)
    all_text  = []
    print(f"   → {num_pages} page(s) — sending to Groq vision...")

    for page_num, page in enumerate(doc, start=1):
        print(f"   → Extracting page {page_num}/{num_pages}...")
        b64 = _page_to_base64_png(page)
        msg = HumanMessage(content=[
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            {"type": "text", "text": (
                f"Page {page_num} of {num_pages}. "
                "Extract and return ALL text exactly as it appears. "
                "Preserve dates, names, addresses, headings, paragraphs. "
                "Do not summarise — return the full text verbatim."
            )},
        ])
        page_text = vision_llm.invoke([msg]).content.strip()
        all_text.append(f"--- Page {page_num} ---\n{page_text}")

    doc.close()
    return "\n\n".join(all_text)


# ═══════════════════════════════════════════════════════════
# 7.  AGENT NODES
# ═══════════════════════════════════════════════════════════

def memory_check_agent(state: AgentState) -> dict:
    """Check audit log for duplicate documents before processing."""
    print("\n🧠 [Memory Agent] Checking for prior record...")

    with _span("memory_check_agent") as span:
        _set_attrs(span, **{"document.name": state["document_name"]})

        prior = None
        if Path(AUDIT_FILE).exists():
            with open(AUDIT_FILE) as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get("document_name") == state["document_name"]:
                            prior = entry
                    except Exception:
                        pass

        if prior:
            prev_class = prior.get("classification", "unknown")
            prev_time  = prior.get("timestamp", "")[:10]
            msg        = f"Duplicate — previously classified as '{prev_class}' on {prev_time}"
            print(f"   → {msg}")
            _set_attrs(span, **{
                "memory.duplicate":      True,
                "memory.previous_class": prev_class,
                "memory.previous_date":  prev_time,
            })
            return {
                "duplicate_detected":    True,
                "classification":        prev_class,
                "classification_reason": msg,
                "action_taken":          "Skipped (duplicate)",
                "audit_log": [{
                    "agent":     "MemoryAgent",
                    "action":    msg,
                    "timestamp": datetime.now().isoformat(),
                }],
            }

        print("   → No prior record — processing fresh.")
        _set_attrs(span, **{"memory.duplicate": False})
        return {
            "duplicate_detected": False,
            "audit_log": [{
                "agent":     "MemoryAgent",
                "action":    "No prior record — fresh processing",
                "timestamp": datetime.now().isoformat(),
            }],
        }


def document_loader_agent(state: AgentState) -> dict:
    """Extract PDF text via Groq vision (no PdfReader)."""
    name = Path(state["pdf_path"]).name
    print(f"\n📄 [Document Loader] Sending '{name}' to Groq vision...")

    with _span("document_loader_agent") as span:
        _set_attrs(span, **{
            "document.name": name,
            "document.path": state["pdf_path"],
        })
        text = _llm_extract_pdf(state["pdf_path"])
        print(f"   → Extracted {len(text)} chars")
        _set_attrs(span, **{"document.extracted_chars": len(text)})
        return {
            "document_text": text,
            "document_name": name,
            "audit_log": [{
                "agent":     "DocumentLoaderAgent",
                "action":    f"LLM-extracted '{name}' ({len(text)} chars)",
                "timestamp": datetime.now().isoformat(),
            }],
        }


# ── Classification prompt ──────────────────────────────────
CLASSIFY_PROMPT = f"""You are a senior legal document analyst specialising in Cease & Desist (C&D) letters.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — CONFIDENCE SCORING (0-100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Add points for each present signal:
  +20  Explicit "Cease and Desist" or "Stop and Desist" language
  +20  Identified sender with name and/or address
  +15  Clear statement of the activity to stop
  +15  Demand for acknowledgement or response
  +10  Legal consequences or threats mentioned
  +10  Deadline or timeframe given
  +10  Attorney or legal representative involvement

Deduct points for each:
  -20  No explicit "cease" or "stop" demand
  -15  Sender identity unclear or missing
  -15  Activity to stop is vague or absent
  -10  Document is clearly something else
  -10  Language is ambiguous

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — CLASSIFICATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classify the document as ONE of: "cease", "uncertain", or "irrelevant".

  "cease"
    → Document clearly demands the recipient stop specific activities
    → Must have: identifiable sender + specific activity + stop demand

  "uncertain"
    → Document IS C&D-related BUT missing key elements or intent unclear
    → ⚠️  Use ONLY for C&D-related but ambiguous documents
    → ⚠️  Do NOT use for documents clearly not C&D related

  "irrelevant"
    → Clearly NOT a cease & desist — no ambiguity
    → Examples: invoice, LOA, complaint, NDA, contract, marketing letter,
      settlement proposal, guardianship request, billing dispute

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROUTING RULE — CONFIDENCE THRESHOLD: {CONFIDENCE_THRESHOLD}%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  confidence > {CONFIDENCE_THRESHOLD}%   → auto-processed (cease → DB, irrelevant → archive)
  confidence <= {CONFIDENCE_THRESHOLD}%  → ALWAYS sent to human review (HITL)
                    This applies to BOTH cease AND irrelevant classifications.
                    Only extremely certain documents bypass human review.

  ROUTING TABLE:
  ┌──────────────────────────────────────┬─────────────┬──────────┐
  │ Scenario                             │ Class       │ Route    │
  ├──────────────────────────────────────┼─────────────┼──────────┤
  │ Any doc, confidence > {CONFIDENCE_THRESHOLD}%, C&D     │ cease       │ Database │
  │ Any doc, confidence > {CONFIDENCE_THRESHOLD}%, not C&D │ irrelevant  │ Archive  │
  │ Any doc, confidence <= {CONFIDENCE_THRESHOLD}%         │ → HITL      │ Human    │
  │ C&D-like but key parts missing       │ uncertain   │ Human    │
  └──────────────────────────────────────┴─────────────┴──────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — EXTRACTION  (use "unknown" if absent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  sender_name       – Full legal name of sender or their attorney
  sender_address    – Postal/mailing address
  cease_activity    – Specific activity that must stop (be precise)
  irrelevant_reason – If irrelevant: document type + why not a C&D
                      (empty string if cease or uncertain)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — OUTPUT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Reply ONLY with valid JSON — no markdown, no extra text.
Always include confidence_score for ALL classification types.

Cease example:
{{"classification":"cease","confidence_score":100,"reason":"Explicit C&D from attorney demanding stop of trademark use","sender_name":"Jane Doe","sender_address":"123 Legal St, Austin TX","cease_activity":"Use of trademark XYZ in commercial products","irrelevant_reason":""}}

Uncertain example:
{{"classification":"uncertain","confidence_score":67,"reason":"Appears C&D-related but sender identity missing","sender_name":"unknown","sender_address":"unknown","cease_activity":"Distribution of copyrighted material","irrelevant_reason":""}}

Irrelevant example:
{{"classification":"irrelevant","confidence_score":100,"reason":"Document is a vendor invoice, not a legal demand","sender_name":"Acme Corp","sender_address":"unknown","cease_activity":"unknown","irrelevant_reason":"Payment invoice for software services. No legal demand, no cease language."}}"""


def classification_agent(state: AgentState) -> dict:
    """
    Classify document and route based on confidence threshold.

    Routing rule (CONFIDENCE_THRESHOLD = 99%):
      confidence > 99%  → auto-route as cease or irrelevant
      confidence <= 99% → ALWAYS HITL, regardless of classification
                          (this includes both cease AND irrelevant)
    """
    print(f"\n🔍 [Classification Agent] Classifying via {TEXT_MODEL}...")

    with _span("classification_agent") as span:
        _set_attrs(span, **{
            "document.name":         state["document_name"],
            "document.chars":        len(state.get("document_text", "")),
            "confidence.threshold":  CONFIDENCE_THRESHOLD,
        })

        messages = [
            SystemMessage(content=CLASSIFY_PROMPT),
            HumanMessage(content=f"Document content:\n\n{state['document_text'][:5000]}"),
        ]
        raw = llm.invoke(messages).content.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {
                "classification":    "uncertain",
                "confidence_score":  0,
                "reason":            "Could not parse LLM response — routing to HITL.",
                "irrelevant_reason": "",
                "sender_name":       "unknown",
                "sender_address":    "unknown",
                "cease_activity":    "unknown",
            }

        raw_class  = result.get("classification", "uncertain")
        confidence = max(0, min(100, int(result.get("confidence_score", 0))))
        reason     = result.get("reason", "")

        # ── Confidence-based routing ───────────────────────────
        # Rule: confidence must be STRICTLY ABOVE threshold to auto-route.
        # This applies to BOTH cease AND irrelevant.
        # Anything at or below threshold → HITL, no exceptions.
        if confidence > CONFIDENCE_THRESHOLD:
            routed_class = raw_class   # "cease" or "irrelevant"
            routing_note = (
                f"confidence {confidence}% > {CONFIDENCE_THRESHOLD}% "
                f"→ auto '{raw_class}'"
            )
        else:
            # Below threshold: send to HITL regardless of what LLM said
            routed_class = "hitl_needed"
            routing_note = (
                f"confidence {confidence}% <= {CONFIDENCE_THRESHOLD}% "
                f"→ HITL (LLM said '{raw_class}' but confidence too low)"
            )

        print(f"   → LLM class    : {raw_class.upper()}")
        print(f"   → Confidence   : {confidence}%")
        print(f"   → Threshold    : {CONFIDENCE_THRESHOLD}%")
        print(f"   → Route        : {'✅ AUTO' if routed_class != 'hitl_needed' else '⚠️  HITL'} — {routing_note}")

        _set_attrs(span, **{
            "classification.result":     routed_class,
            "classification.raw":        raw_class,
            "classification.confidence": confidence,
            "classification.reason":     reason,
            "classification.auto_routed": routed_class != "hitl_needed",
        })

        return {
            "classification":        routed_class,
            "classification_reason": reason,
            "confidence_score":      confidence,
            "irrelevant_reason":     result.get("irrelevant_reason", ""),
            "extracted_details": {
                "sender_name":    result.get("sender_name",    "unknown"),
                "sender_address": result.get("sender_address", "unknown"),
                "cease_activity": result.get("cease_activity", "unknown"),
                "raw_class":      raw_class,
            },
            "audit_log": [{
                "agent":     "ClassificationAgent",
                "action":    (
                    f"LLM='{raw_class}' confidence={confidence}% "
                    f"threshold={CONFIDENCE_THRESHOLD}% → routed='{routed_class}'"
                ),
                "reason":    reason,
                "timestamp": datetime.now().isoformat(),
            }],
        }


def database_agent(state: AgentState) -> dict:
    """Store valid cease requests in SQLite."""
    print("\n🗄️  [Database Agent] Storing cease request...")

    with _span("database_agent") as span:
        d = state.get("extracted_details", {})
        _set_attrs(span, **{
            "document.name":       state["document_name"],
            "document.confidence": state.get("confidence_score", 0),
            "sender.name":         d.get("sender_name", "unknown"),
            "cease.activity":      d.get("cease_activity", "unknown"),
        })
        result = store_cease_request.invoke({
            "received_date":  datetime.now().strftime("%Y-%m-%d"),
            "document_name":  state["document_name"],
            "sender_name":    d.get("sender_name",    "unknown"),
            "sender_address": d.get("sender_address", "unknown"),
            "cease_activity": d.get("cease_activity", "unknown"),
            "confidence":     state.get("confidence_score", 0),
            "raw_text":       state.get("document_text", ""),
        })
        print(f"   → {result}")
        _set_attrs(span, **{"action.result": result})
        return {
            "action_taken": result,
            "audit_log": [{"agent": "DatabaseAgent", "action": result,
                           "timestamp": datetime.now().isoformat()}],
        }


def archiving_agent(state: AgentState) -> dict:
    """Archive irrelevant documents with confidence score and reason."""
    print("\n📁 [Archiving Agent] Archiving irrelevant document...")

    with _span("archiving_agent") as span:
        reason = (
            state.get("irrelevant_reason")
            or state.get("classification_reason")
            or "Not a cease & desist document"
        )
        _set_attrs(span, **{
            "document.name":       state["document_name"],
            "document.confidence": state.get("confidence_score", 0),
            "irrelevant.reason":   reason,
        })
        result = archive_irrelevant_document.invoke({
            "received_date": datetime.now().strftime("%Y-%m-%d"),
            "document_name": state["document_name"],
            "reason":        reason,
            "confidence":    state.get("confidence_score", 0),
        })
        print(f"   → {result}")
        _set_attrs(span, **{"action.result": result})
        return {
            "action_taken": result,
            "audit_log": [{"agent": "ArchivingAgent", "action": result,
                           "timestamp": datetime.now().isoformat()}],
        }


def hitl_agent(state: AgentState) -> dict:
    """
    Web mode : parks doc for human review via POST /hitl-decision.
    CLI mode : falls back to console input().
    """
    raw_class  = state.get("extracted_details", {}).get("raw_class", "unknown")
    confidence = state.get("confidence_score", 0)

    with _span("hitl_agent") as span:
        _set_attrs(span, **{
            "document.name":             state["document_name"],
            "hitl.mode":                 "web" if os.environ.get("WEB_MODE") == "1" else "cli",
            "classification.suggested":  raw_class,
            "classification.confidence": confidence,
            "confidence.threshold":      CONFIDENCE_THRESHOLD,
        })

        # ── Web mode ──
        if os.environ.get("WEB_MODE") == "1":
            print(f"\n👤 [HITL Agent] Parking '{state['document_name']}' for web review...")
            print(f"   → LLM said '{raw_class}' at {confidence}% — below {CONFIDENCE_THRESHOLD}% threshold")
            _set_attrs(span, **{"hitl.parked": True})
            return {
                "classification": "hitl_needed",
                "audit_log": [{
                    "agent":     "HITLAgent",
                    "action":    (
                        f"Parked for web review — LLM said '{raw_class}' "
                        f"({confidence}%) but confidence <= {CONFIDENCE_THRESHOLD}%"
                    ),
                    "timestamp": datetime.now().isoformat(),
                }],
            }

        # ── CLI fallback ──
        print("\n" + "─" * 64)
        print("👤  HUMAN REVIEW REQUIRED")
        print(f"   Document       : {state['document_name']}")
        print(f"   LLM suggested  : {raw_class.upper()}")
        print(f"   Confidence     : {confidence}%  (threshold: {CONFIDENCE_THRESHOLD}%)")
        print(f"   Reason         : {state['classification_reason']}")
        if state.get("irrelevant_reason"):
            print(f"   Irrelevant note: {state['irrelevant_reason']}")
        print(f"\n   Preview:")
        for line in state.get("document_text", "")[:400].splitlines():
            print(f"     {line}")
        print("─" * 64)
        print("\n   [1] cease      – Valid cease & desist")
        print("   [2] irrelevant – Not a cease & desist")

        while True:
            c = input("\n   Enter 1 or 2: ").strip()
            if c == "1":
                decision = "cease"
                hr       = ""
                break
            elif c == "2":
                decision = "irrelevant"
                hr       = input("   Brief reason it is irrelevant: ").strip()
                break
            else:
                print("   Please enter 1 or 2.")

        print(f"   → Human decided: {decision.upper()}")
        _set_attrs(span, **{"hitl.human_decision": decision})
        return {
            "human_decision":    decision,
            "classification":    decision,
            "irrelevant_reason": hr or state.get("irrelevant_reason", ""),
            "audit_log": [{
                "agent":       "HITLAgent",
                "action":      f"CLI: Human overrode '{raw_class}' ({confidence}%) → '{decision}'",
                "timestamp":   datetime.now().isoformat(),
                "reviewed_by": "human_operator",
            }],
        }


def audit_agent(state: AgentState) -> dict:
    """Write final compliance audit entry — always runs last."""
    print("\n📝 [Audit Agent] Writing compliance entry...")

    with _span("audit_agent") as span:
        reviewed_by = "human_operator" if state.get("human_decision") else "system"
        final_class = (
            state.get("human_decision")
            or state.get("extracted_details", {}).get("raw_class")
            or state.get("classification")
            or "unknown"
        )
        _set_attrs(span, **{
            "document.name":             state["document_name"],
            "classification.final":      final_class,
            "classification.confidence": state.get("confidence_score", 0),
            "reviewed_by":               reviewed_by,
        })
        result = write_audit_entry.invoke({
            "document_name":  state["document_name"],
            "classification": final_class,
            "reason":         state.get("classification_reason") or "No reason provided",
            "confidence":     state.get("confidence_score") or 0,
            "action":         state.get("action_taken") or "none",
            "reviewed_by":    reviewed_by,
        })
        print(f"   → {result}")
        return {
            "audit_log": [{"agent": "AuditAgent", "action": result,
                           "timestamp": datetime.now().isoformat()}],
        }


# ═══════════════════════════════════════════════════════════
# 8.  ROUTING
# ═══════════════════════════════════════════════════════════

def route_after_memory(state: AgentState) -> str:
    if state.get("duplicate_detected"):
        return "audit"
    return "document_loader"


def route_classification(state: AgentState) -> str:
    c = state.get("classification", "hitl_needed")
    if c == "cease":      return "database"
    if c == "irrelevant": return "archiving"
    return "hitl"   # "hitl_needed" or anything else


def route_hitl(state: AgentState) -> str:
    return "database" if state.get("human_decision") == "cease" else "archiving"


# ═══════════════════════════════════════════════════════════
# 9.  GRAPH
# ═══════════════════════════════════════════════════════════

def build_graph():
    g = StateGraph(AgentState)

    g.add_node("memory_check",    memory_check_agent)
    g.add_node("document_loader", document_loader_agent)
    g.add_node("classification",  classification_agent)
    g.add_node("database",        database_agent)
    g.add_node("archiving",       archiving_agent)
    g.add_node("hitl",            hitl_agent)
    g.add_node("audit",           audit_agent)

    g.set_entry_point("memory_check")

    g.add_conditional_edges(
        "memory_check", route_after_memory,
        {"document_loader": "document_loader", "audit": "audit"},
    )
    g.add_edge("document_loader", "classification")
    g.add_conditional_edges(
        "classification", route_classification,
        {"database": "database", "archiving": "archiving", "hitl": "hitl"},
    )
    g.add_conditional_edges(
        "hitl", route_hitl,
        {"database": "database", "archiving": "archiving"},
    )
    g.add_edge("database",  "audit")
    g.add_edge("archiving", "audit")
    g.add_edge("audit",     END)

    return g.compile(checkpointer=MemorySaver())


# ═══════════════════════════════════════════════════════════
# 10.  SINGLE DOCUMENT RUNNER  (root trace span)
# ═══════════════════════════════════════════════════════════

def process_document(pdf_path: str, thread_id: str = None) -> dict:
    """
    Run one PDF through the full 7-agent pipeline under ONE root trace.

    Tracing: all agent spans are automatically children of this root
    because app.invoke() runs synchronously on the same thread.
    Phoenix shows: 1 trace per document with 5-7 nested child spans.
    """
    doc_name = Path(pdf_path).name
    tid      = thread_id or Path(pdf_path).stem

    with _span("process_document") as root_span:
        _set_attrs(root_span, **{
            "document.name":         doc_name,
            "document.path":         pdf_path,
            "thread.id":             tid,
            "pipeline.version":      "2.0",
            "confidence.threshold":  CONFIDENCE_THRESHOLD,
        })

        app = build_graph()
        initial: AgentState = {
            "pdf_path":              pdf_path,
            "document_text":         "",
            "document_name":         doc_name,
            "classification":        None,
            "classification_reason": "",
            "confidence_score":      0,
            "irrelevant_reason":     "",
            "extracted_details":     {},
            "human_decision":        None,
            "action_taken":          "",
            "duplicate_detected":    False,
            "audit_log":             [],
        }

        final = app.invoke(initial, config={"configurable": {"thread_id": tid}})

        # Annotate root span with final outcome
        _set_attrs(root_span, **{
            "result.classification": str(final.get("classification",     "unknown")),
            "result.confidence":     int(final.get("confidence_score",   0)),
            "result.action":         str(final.get("action_taken",       "none")),
            "result.duplicate":      bool(final.get("duplicate_detected", False)),
            "result.human_reviewed": bool(final.get("human_decision")),
        })

        return final


def _print_result(final: dict, idx: int, total: int) -> None:
    confidence = final.get("confidence_score", 0)
    filled     = int(confidence / 5)
    bar        = "█" * filled + "░" * (20 - filled)
    print(f"\n{'═' * 64}")
    print(f"  [{idx}/{total}] {final.get('document_name', '?')}")
    if final.get("duplicate_detected"):
        print("  ⚠️  DUPLICATE — previously processed")
    print(f"  Classification : {(final.get('classification') or '?').upper()}")
    print(f"  Confidence     : [{bar}] {confidence}%")
    print(f"  Threshold      : {CONFIDENCE_THRESHOLD}%  {'✅ auto-routed' if confidence > CONFIDENCE_THRESHOLD else '⚠️  HITL'}")
    print(f"  Action         : {final.get('action_taken', 'none')}")
    if final.get("human_decision"):
        print(f"  Human decision : {final['human_decision'].upper()}")
    print(f"{'═' * 64}")


# ═══════════════════════════════════════════════════════════
# 11.  FOLDER BATCH PROCESSOR
# ═══════════════════════════════════════════════════════════

def process_folder(folder_path: str) -> list:
    folder    = Path(folder_path)
    pdf_files = sorted(folder.glob("*.pdf"))

    if not pdf_files:
        print(f"⚠️  No PDF files found in '{folder_path}'.")
        sys.exit(0)

    total   = len(pdf_files)
    counts  = {"cease": 0, "irrelevant": 0, "hitl": 0, "duplicate": 0, "error": 0}
    results = []

    print(f"\n📂  Found {total} PDF(s) in '{folder}'")
    print(f"   Confidence threshold: {CONFIDENCE_THRESHOLD}%")
    print("─" * 64)
    for i, p in enumerate(pdf_files, 1):
        print(f"  {i:>3}. {p.name}")
    print("─" * 64)

    for idx, pdf in enumerate(pdf_files, 1):
        print(f"\n\n🔄  Processing {idx}/{total}: {pdf.name}")
        try:
            final = process_document(str(pdf), thread_id=pdf.stem)
            results.append(final)
            _print_result(final, idx, total)
            if final.get("duplicate_detected"):
                counts["duplicate"] += 1
            else:
                c = (final.get("human_decision") or final.get("classification") or "").lower()
                if "cease"        in c: counts["cease"]      += 1
                elif "irrelevant" in c: counts["irrelevant"] += 1
                else:                   counts["hitl"]       += 1
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({"document_name": pdf.name, "error": str(e)})
            counts["error"] += 1

    print(f"\n\n{'═' * 64}")
    print("📊  BATCH SUMMARY")
    print(f"{'─' * 64}")
    print(f"  Total            : {total}")
    print(f"  ✅ Cease         : {counts['cease']}")
    print(f"  📁 Irrelevant    : {counts['irrelevant']}")
    print(f"  👤 HITL reviews  : {counts['hitl']}")
    print(f"  🔁 Duplicates    : {counts['duplicate']}")
    if counts["error"]:
        print(f"  ❌ Errors        : {counts['error']}")
    print(f"\n  Output → {DB_PATH}, {ARCHIVE_FILE}, {AUDIT_FILE}")
    print(f"  Traces → http://localhost:6006")
    print(f"{'═' * 64}\n")
    return results


# ═══════════════════════════════════════════════════════════
# 12.  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python run_langgraph.py sample_docs/         ← folder")
        print("  python run_langgraph.py sample_docs/doc.pdf  ← single file")
        sys.exit(1)

    target = sys.argv[1]
    if Path(target).is_dir():
        process_folder(target)
    elif Path(target).is_file() and target.lower().endswith(".pdf"):
        final = process_document(target)
        _print_result(final, 1, 1)
    else:
        print(f"❌  '{target}' is not a valid PDF or folder.")
        sys.exit(1)
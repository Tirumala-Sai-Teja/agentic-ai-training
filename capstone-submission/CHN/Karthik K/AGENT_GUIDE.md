# 🤖 Agent & Function Reference Guide

Complete reference for every agent, tool, function, and design decision in the Cease & Desist Document Processing System.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Agents](#agents)
3. [Tools](#tools)
4. [Observability — Arize Phoenix](#observability--arize-phoenix)
5. [Classification Prompt Design](#classification-prompt-design)
6. [Confidence Scoring & Routing](#confidence-scoring--routing)
7. [State Management](#state-management)
8. [Routing Logic](#routing-logic)
9. [Graph Structure](#graph-structure)
10. [API Server Design](#api-server-design)
11. [Frontend Components](#frontend-components)
12. [Data Flow Walkthrough](#data-flow-walkthrough)

---

## System Overview

Built on **LangGraph** — a framework for stateful, multi-step AI workflows. Each agent is a Python function that receives the shared `AgentState`, performs one specific job, and returns updated fields.

### The 7 Agents (execution order)

```
1. memory_check_agent     → Checked audit log — seen before? Skip. New? Continue.
2. document_loader_agent  → PDF → PNG pages → Groq vision → extracted text
3. classification_agent   → llama-3.3-70b: what is this? Score 0-100 honestly.
4. database_agent         → Store valid cease requests in SQLite
5. archiving_agent        → Archive irrelevant docs with reason to flat file
6. hitl_agent             → Park for human review (web modal or CLI prompt)
7. audit_agent            → Write JSONL compliance entry — always runs last
```

### Tracing design

Each call to `process_document()` creates **one root span** in Arize Phoenix. All 7 agent spans are automatically nested under it because `app.invoke()` runs synchronously on the same thread — OpenTelemetry's thread-local context propagates naturally.

```
process_document  ← root span
  ├── memory_check_agent
  ├── document_loader_agent
  │     └── [Groq vision calls — auto-instrumented]
  ├── classification_agent
  │     └── [Groq text call — auto-instrumented]
  ├── database_agent / archiving_agent
  └── audit_agent
```

---

## Agents

### 1. `memory_check_agent`

**File:** `run_langgraph.py`
**Span:** `memory_check_agent`
**Purpose:** Prevents reprocessing documents that have already been handled.

**How it works:**
- Reads `audit_log.jsonl` line by line
- Searches for `document_name` matching current document
- If found: sets `duplicate_detected=True`, copies previous classification, routes straight to `audit_agent`
- If not found: allows normal processing to continue

**Why audit log instead of database:**
The database only stores valid cease requests. The audit log stores every document (cease, irrelevant, uncertain), making it the complete record for duplicate detection.

**Traced attributes:**
- `document.name`
- `memory.duplicate` (bool)
- `memory.previous_class`
- `memory.previous_date`

**State fields set:**
- `duplicate_detected` → `True` or `False`
- `classification` → copied from previous audit entry (if duplicate)
- `classification_reason` → "Duplicate — previously classified as '...' on ..."
- `action_taken` → "Skipped (duplicate)"

---

### 2. `document_loader_agent`

**File:** `run_langgraph.py`
**Span:** `document_loader_agent`
**Purpose:** Extracts all text from a PDF using the Groq vision model. No OCR library — each page is a PNG image sent to AI.

**How it works:**
1. Opens PDF with PyMuPDF (`fitz`)
2. Renders each page at 150 DPI → PNG bytes → base64 string
3. Sends each image to `meta-llama/llama-4-scout-17b-16e-instruct` via Groq
4. Collects text response per page
5. Joins all pages with `--- Page N ---` separators

**Why vision extraction:**
Works on scanned PDFs and image-based documents where traditional text layer extraction fails. No dependency on the PDF having a parseable text layer.

**Traced attributes:**
- `document.name`
- `document.path`
- `document.extracted_chars`

**Helper functions:**
- `_page_to_base64_png(page)` — renders one PyMuPDF page to base64 PNG at 150 DPI
- `_llm_extract_pdf(pdf_path)` — orchestrates multi-page extraction loop

**State fields set:**
- `document_text` — full extracted text from all pages
- `document_name` — filename only (e.g. `cease_letter.pdf`)

---

### 3. `classification_agent`

**File:** `run_langgraph.py` and `agents/classification_agent.py`
**Span:** `classification_agent`
**Purpose:** The core intelligence — classifies the document type, scores confidence against mandatory C&D criteria, and extracts key fields.

**Critical design decisions:**

**1. Threshold is hidden from the LLM**
The routing cutoff (95%) is never shown in the prompt. If the LLM knows the threshold it games the score (returns 100 to force auto-routing). With the threshold hidden, the LLM scores honestly based only on what it reads in the document.

**2. Criteria-based scoring, not abstract self-assessment**
Instead of asking "how confident are you?", the prompt asks the LLM to check three specific mandatory criteria:

```
[A] EXPLICIT DEMAND TO STOP
    Words like: "cease and desist", "immediately stop",
    "cease all", "demand that you stop", "refrain from",
    "discontinue", "halt"
    ❌ Vague requests, settlement proposals do NOT qualify

[B] IDENTIFIABLE SENDER
    Named person, company, or legal representative
    ❌ Anonymous sender does NOT qualify

[C] SPECIFIC ACTIVITY TO STOP
    Trademark use, copyright infringement, harassment,
    breach of contract, defamation — must be specific
    ❌ "stop everything" does NOT qualify
```

ALL THREE must be present for "cease". Any missing → "uncertain".

**3. No defaults, no caps on the confidence score**
The code extracts whatever integer the LLM returns (0–100). If unparseable or missing → `None` → routes to HITL. No code-side number is ever substituted.

**Routing logic (in code, not prompt):**
```python
if confidence is not None and confidence > CONFIDENCE_THRESHOLD:
    routed_class = raw_class        # auto-route
else:
    routed_class = "hitl_needed"   # HITL (confidence too low or missing)
```

**Traced attributes:**
- `document.name`
- `document.chars`
- `classification.result` (routed class)
- `classification.raw` (LLM's original label)
- `classification.confidence`
- `classification.reason`
- `classification.auto_routed` (bool)
- `confidence.threshold`

**State fields set:**
- `classification` → `"cease"` | `"irrelevant"` | `"hitl_needed"`
- `classification_reason` — one sentence from LLM
- `confidence_score` — integer 0–100, or `None`
- `irrelevant_reason` — why it's not a C&D (if irrelevant)
- `extracted_details` → dict with `sender_name`, `sender_address`, `cease_activity`, `raw_class`

---

### 4. `database_agent`

**File:** `run_langgraph.py`
**Span:** `database_agent`
**Purpose:** Stores confirmed cease & desist requests in SQLite. Runs only when classification is `"cease"` with confidence > 95%, or after a human confirms via HITL.

**Database table: `cease_requests`**

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER | Auto-increment primary key |
| `received_date` | TEXT | Date processed (YYYY-MM-DD) |
| `document_name` | TEXT | PDF filename |
| `sender_name` | TEXT | Extracted sender name |
| `sender_address` | TEXT | Extracted sender address |
| `cease_activity` | TEXT | What must stop |
| `confidence` | INTEGER | Model's confidence score |
| `raw_text` | TEXT | First 2000 chars of document |
| `created_at` | TEXT | ISO timestamp |

**SQLite WAL mode:**
The database uses Write-Ahead Logging (`PRAGMA journal_mode=WAL`) to prevent "database is locked" errors when multiple processes access it simultaneously.

**Traced attributes:**
- `document.name`
- `document.confidence`
- `sender.name`
- `cease.activity`
- `action.result`

---

### 5. `archiving_agent`

**File:** `run_langgraph.py`
**Span:** `archiving_agent`
**Purpose:** Archives irrelevant documents to a flat text file, including the specific reason the document was deemed irrelevant.

**Archive format:**
```
2026-03-18 | invoice_q1.pdf | confidence: 88% | reason: Vendor invoice for software services. No legal demand, no cease language.
```

**Reason priority:**
1. `irrelevant_reason` from LLM (most specific)
2. `classification_reason` (fallback)
3. "Not a cease & desist document" (last resort)

**Traced attributes:**
- `document.name`
- `document.confidence`
- `irrelevant.reason`
- `action.result`

---

### 6. `hitl_agent`

**File:** `run_langgraph.py`
**Span:** `hitl_agent`
**Purpose:** Handles the Human-in-the-Loop checkpoint for low-confidence documents.

**Two modes:**

**Web mode** (`WEB_MODE=1` — set by `server.py` at startup):
- Does NOT call `input()` — would block the server thread forever
- Sets `classification = "hitl_needed"` and returns immediately
- Server parks the full `AgentState` in `pending_hitl` dict (in-memory)
- Frontend shows purple "Review →" button
- Human submits decision via `POST /hitl-decision`
- Server resumes: calls `database_agent` or `archiving_agent` directly

**CLI mode** (running `run_langgraph.py` directly):
- Prints document details and preview to terminal
- Calls `input()` — waits for `1` (cease) or `2` (irrelevant)
- For irrelevant: asks for a brief reason
- Continues pipeline with human decision

**Traced attributes:**
- `document.name`
- `hitl.mode` ("web" or "cli")
- `classification.suggested`
- `classification.confidence`
- `confidence.threshold`
- `hitl.parked` (bool — web mode only)
- `hitl.human_decision` (cli mode only)

---

### 7. `audit_agent`

**File:** `run_langgraph.py`
**Span:** `audit_agent`
**Purpose:** The final node — always runs regardless of which path was taken. Writes a complete compliance record.

**Always runs because:**
- Cease path: `database_agent → audit_agent`
- Irrelevant path: `archiving_agent → audit_agent`
- Duplicate path: `memory_check_agent → audit_agent` (skips all middle agents)
- HITL path: `hitl → database/archiving → audit_agent`

**Audit entry format:**
```json
{
  "timestamp": "2026-03-18T10:23:11.456789",
  "document_name": "cease_letter.pdf",
  "classification": "cease",
  "confidence": 94,
  "reason": "Explicit C&D from attorney demanding stop of trademark use",
  "action": "Stored cease request for 'cease_letter.pdf' (confidence: 94%).",
  "reviewed_by": "system"
}
```

`reviewed_by` is `"human_operator"` if HITL was involved, otherwise `"system"`.

**Traced attributes:**
- `document.name`
- `classification.final`
- `classification.confidence`
- `reviewed_by`

---

## Tools

Tools are `@tool`-decorated functions that perform side effects (storage, file writing).

### `store_cease_request`

```python
store_cease_request(
    received_date, document_name, sender_name,
    sender_address, cease_activity, confidence, raw_text
) -> str
```

Inserts a row into `cease_requests` SQLite table. Uses `timeout=30` and `PRAGMA journal_mode=WAL` to prevent lock conflicts.

---

### `archive_irrelevant_document`

```python
archive_irrelevant_document(
    received_date, document_name, reason, confidence
) -> str
```

Appends one line to `irrelevant_documents.txt`. Includes confidence score and specific reason.

---

### `write_audit_entry`

```python
write_audit_entry(
    document_name, classification, reason,
    confidence, action, reviewed_by
) -> str
```

Appends one JSON line to `audit_log.jsonl`. This file is also read by `memory_check_agent` for duplicate detection — it is the single source of truth for all processed documents.

---

## Observability — Arize Phoenix

### Setup

```bash
pip install arize-phoenix arize-phoenix-otel opentelemetry-sdk

# Start BEFORE server.py
python -m phoenix.server.main &
open http://localhost:6006
```

### How tracing works

`_setup_tracing()` in `run_langgraph.py` registers Phoenix with `auto_instrument=True`:

```python
from phoenix.otel import register
register(project_name="cease-desist-processor", auto_instrument=True)
tracer = trace.get_tracer("cease_desist_pipeline")
```

`auto_instrument=True` automatically traces all LangChain and Groq calls without any manual instrumentation — every LLM call shows token counts and latency.

The root span is opened in `process_document()`:

```python
with _span("process_document") as root_span:
    _set_attrs(root_span, document.name=..., thread.id=..., ...)
    final = app.invoke(initial, ...)   # all agents run here
    _set_attrs(root_span, result.classification=..., result.confidence=...)
```

Because `app.invoke()` is synchronous, OpenTelemetry's thread-local context automatically makes every agent's `with _span(...)` a child of the root. No manual context passing needed.

### Graceful fallback

If `arize-phoenix` is not installed, `_setup_tracing()` returns `None` and `_span()` returns `nullcontext()` — the pipeline runs normally without any tracing errors.

### Local storage

All traces are saved to `~/.phoenix/` on your machine. Nothing is sent to the cloud unless you explicitly configure Arize Cloud credentials.

---

## Classification Prompt Design

### Why criteria-based scoring beats abstract confidence

**Old approach (broken):**
> "How confident are you in this classification?" → LLM always returns 90–100

**New approach (working):**
> "Does criterion [A] exist? Does [B] exist? Does [C] exist?" → LLM scores based on what's actually in the document

The three mandatory criteria act as a structured checklist. A missing criterion directly lowers the score rather than being absorbed into a vague "confidence" number.

### Why the threshold is hidden

The prompt never mentions 95% or any routing cutoff. If the LLM sees the threshold it reasons: "This document looks like a C&D. To auto-route it I need to return above 95. I'll return 97." That's score gaming, not honest assessment.

With the threshold hidden, the LLM has no incentive to inflate — it scores based solely on what it reads.

### Scoring guidance in the prompt

```
96–100 : Absolute certainty — every signal present, zero ambiguity
85–95  : Very clear, one or two minor missing elements
70–84  : Reasonably clear but some ambiguity or missing fields
50–69  : Significant ambiguity — multiple signals missing
0–49   : Very unclear or contradictory signals
```

---

## Confidence Scoring & Routing

### Threshold

```python
CONFIDENCE_THRESHOLD = 95   # in run_langgraph.py
```

### Routing table

| LLM score | LLM class | Route |
|---|---|---|
| `> 95` | cease | Database ✅ |
| `> 95` | irrelevant | Archive 📁 |
| `≤ 95` | any | HITL 👤 |
| `None` (missing) | any | HITL 👤 |
| out-of-range | any | HITL 👤 |

### Code implementation (no defaults, no caps)

```python
raw_confidence = result.get("confidence_score")
if raw_confidence is not None:
    try:
        confidence = int(float(str(raw_confidence)))
        if not (0 <= confidence <= 100):
            confidence = None   # out of range → HITL
    except (TypeError, ValueError):
        confidence = None       # unparseable → HITL
else:
    confidence = None           # missing → HITL

# Routing
if confidence is not None and confidence > confidence_threshold:
    routed_class = raw_class    # trust LLM's label
else:
    routed_class = "hitl_needed"
```

---

## State Management

The `AgentState` TypedDict flows through every node:

```python
class AgentState(TypedDict):
    pdf_path:               str           # Input: PDF file path
    document_text:          str           # Set by: document_loader_agent
    document_name:          str           # Set by: document_loader_agent
    classification:         Optional[str] # Set by: classification_agent
                                          # Values: "cease"|"irrelevant"|"hitl_needed"
    classification_reason:  str           # Set by: classification_agent
    confidence_score:       int           # Set by: classification_agent (0-100 or None)
    irrelevant_reason:      str           # Set by: classification_agent or HITL
    extracted_details:      dict          # Set by: classification_agent
                                          # Keys: sender_name, sender_address,
                                          #       cease_activity, raw_class
    human_decision:         Optional[str] # Set by: hitl_agent ("cease"|"irrelevant")
    action_taken:           str           # Set by: database_agent or archiving_agent
    duplicate_detected:     bool          # Set by: memory_check_agent
    audit_log:              List[dict]    # Appended by: every agent
```

The `audit_log` field uses `Annotated[List[dict], operator.add]` — LangGraph merges lists from different nodes rather than replacing them, so every agent's log entry is preserved in the final state.

---

## Routing Logic

### `route_after_memory`

```python
def route_after_memory(state) -> str:
    if state.get("duplicate_detected"):
        return "audit"           # skip all processing, go straight to log
    return "document_loader"     # process normally
```

### `route_classification`

```python
def route_classification(state) -> str:
    c = state.get("classification", "hitl_needed")
    if c == "cease":      return "database"
    if c == "irrelevant": return "archiving"
    return "hitl"               # hitl_needed or any unexpected value
```

### `route_hitl`

```python
def route_hitl(state) -> str:
    return "database" if state.get("human_decision") == "cease" else "archiving"
```

---

## Graph Structure

```python
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

    g.add_conditional_edges("memory_check",   route_after_memory,   {...})
    g.add_edge("document_loader", "classification")
    g.add_conditional_edges("classification", route_classification,  {...})
    g.add_conditional_edges("hitl",           route_hitl,           {...})
    g.add_edge("database",  "audit")
    g.add_edge("archiving", "audit")
    g.add_edge("audit",     END)

    return g.compile(checkpointer=MemorySaver())
```

`MemorySaver` checkpoints state at each step, enabling state inspection and recovery.

---

## API Server Design

### Two-phase HITL flow

```
Phase 1: POST /process
  → process_document() runs pipeline
  → if hitl_needed: park state in pending_hitl dict, return hitl_pending=true

Phase 2: POST /hitl-decision
  → retrieve parked state from pending_hitl
  → apply human decision to state
  → call database_agent or archiving_agent directly
  → call audit_agent
  → return final result
```

### `WEB_MODE=1`

Set at the top of `server.py` before importing the pipeline:

```python
os.environ["WEB_MODE"] = "1"
```

This prevents `hitl_agent` from calling `input()`, which would block the FastAPI server thread permanently. The agent checks this env var and returns immediately in web mode.

### `pending_hitl` dictionary

In-memory store: `document_name → AgentState`. State is parked here between Phase 1 and Phase 2. If the server restarts, pending HITL documents are lost (they would need to be resubmitted).

---

## Frontend Components

### `App`

Main component managing:
- `files` — queued PDFs
- `results` — processed results array
- `hitlDoc` — document open in review modal
- `processing` — loading state
- `pendingCount` — count of docs awaiting review

Key functions:
- `handleProcess()` — `POST /process`, sets `results`
- `handleHitlSubmit(docName, decision, reason)` — `POST /hitl-decision`, updates card in place
- `openReview(result)` — fetches fresh data from `GET /hitl-pending`, opens modal

### `HitlModal`

Review modal for uncertain documents. Shows LLM suggestion, confidence, reason, document preview.

Validation:
- Decision (cease/irrelevant) is required
- Reason is required when decision = irrelevant
- Reason is optional when decision = cease

### `ResultCard`

Expandable card per document. Shows classification, confidence bar, sender details, reason. Purple "Review →" button appears when `hitl_pending=true` and not yet reviewed.

### `ConfidenceBar`

Visual bar with colour coding:
- Green (> 95%) — auto-processed
- Amber (60–95%) — borderline / HITL
- Red (< 60%) — low confidence

### `StatsBar`

Four metric cards: Total, Cease & Desist (green), Irrelevant (red), Needs Review (purple).

---

## Data Flow Walkthrough

### Happy path — clear cease & desist

```
1. User uploads "attorney_cease.pdf"
2. memory_check_agent   → not in audit_log → fresh document
3. document_loader_agent → 2 pages → Groq vision → 3,241 chars
4. classification_agent  → [A]✅ [B]✅ [C]✅ → "cease", confidence 94%
                         → 94% <= 95% → hitl_needed  (below threshold)

   OR if confidence = 96%:
                         → 96% > 95% → auto "cease"
5. database_agent        → INSERT into cease_requests
6. audit_agent           → {"reviewed_by": "system", "confidence": 96}
```

### HITL path — low confidence

```
1. User uploads "vague_demand.pdf"
2. memory_check_agent    → not found → fresh
3. document_loader_agent → 1 page → 847 chars
4. classification_agent  → [A]✅ [B]❌ [C]✅ → "cease", confidence 72%
                         → 72% <= 95% → hitl_needed
5. hitl_agent            → WEB_MODE=1 → parks state → returns hitl_needed
   server.py             → stores in pending_hitl["vague_demand.pdf"]
   API response          → hitl_pending: true → "Review →" shown in UI

6. Human clicks "Review →"
   modal shows: LLM said "cease" at 72%, sender identity unclear
7. Human selects "cease", types "Attorney letterhead confirmed"
8. POST /hitl-decision   → retrieves parked state
9. database_agent        → stores in DB
10. audit_agent          → {"reviewed_by": "human_operator", "confidence": 72}

Result: Green card + "HUMAN REVIEWED" badge
```

### Duplicate path

```
1. User uploads "attorney_cease.pdf" again
2. memory_check_agent → finds in audit_log.jsonl
                      → duplicate_detected=True
                      → routes direct to audit_agent
3. audit_agent        → logs duplicate detection

Result: Card shows previous classification + "DUPLICATE" badge
        No LLM calls made — saves API cost
```

### Irrelevant path

```
1. User uploads "invoice_march.pdf"
2. memory_check_agent    → not found → fresh
3. document_loader_agent → 1 page → 521 chars
4. classification_agent  → [A]❌ [B]✅ [C]❌ → "irrelevant", confidence 91%
                         → 91% <= 95% → hitl_needed (below threshold)

   OR if confidence = 97%:
                         → 97% > 95% → auto "irrelevant"
5. archiving_agent       → appends to irrelevant_documents.txt
6. audit_agent           → {"classification": "irrelevant", "reviewed_by": "system"}
```

from datetime import datetime
from fileinput import filename
import json
import os
import re
import shutil
import sqlite3
from dotenv import load_dotenv
from typing import Annotated
from numpy import number
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from typing import Annotated, Literal
import operator
from pydantic import BaseModel, Field, field_validator
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
groq_api_key = os.getenv('GROQ_API_KEY')


CLASSIFY_PROMPT = """
You are a legal document classification expert specializing in customer communication compliance for the Bank (Wells Fargo).

## TASK
Analyze the provided document and classify it into exactly ONE of the following three categories:

### CATEGORIES

1. CEASE  — Valid Cease & Desist Request
   - Customer explicitly or clearly requests to STOP all direct communication
   - Phrases like: "stop contacting me", "do not call", "no further communication",
     "cease all contact", "I do not wish to be contacted", "remove me from your list"
   - May reference legal rights (TCPA, FDCPA, DNC registry, GDPR, etc.)
   - Intent to stop communication is CLEAR and UNAMBIGUOUS

2. UNCERTAIN — Requires Manual Review
   - Some signals of a cease & desist but unclear or incomplete
   - Ambiguous, indirect, or emotionally driven without clear stop-contact intent
   - Mixed signals, partial opt-out, or contradictory statements
   - Not confident enough to classify as CEASE or IRRELEVANT

3. IRRELEVANT — Not a Cease & Desist Request
   - NO indication of a desire to stop communication
   - General complaints, inquiries, billing disputes, service requests, feedback

## DOCUMENT TO ANALYZE
{document_text}

## OUTPUT FORMAT
Respond ONLY in the following JSON format with no additional text or markdown:

{{
  "classification": "<CEASE | UNCERTAIN | IRRELEVANT>",
  "confidence_score": <integer 1-100>,
  "reasoning": "<2-3 sentences>",
  "key_phrases": ["<phrase1>", "<phrase2>", "<phrase3>"],
  "urgency_level": "<HIGH | MEDIUM | LOW>",
  "recommended_action": "<one line next step>"
}}

## SCORING GUIDANCE
85-100 → CEASE       : Explicit unambiguous request, possibly with legal citations
70-84  → CEASE       : Clear intent, informal but direct
40-69  → UNCERTAIN   : Ambiguous, mixed signals
20-39  → UNCERTAIN   : Weak signals, human review required
1-19   → IRRELEVANT  : No cease & desist indicators

## CRITICAL RULES
- When in doubt, prefer UNCERTAIN over IRRELEVANT (safer to escalate than to miss)
- NEVER classify as CEASE unless intent is explicit or strongly implied
- key_phrases must be direct quotes from the document, not paraphrased
"""


llm = ChatGroq(model=os.getenv('MODEL_NAME'), temperature=float(os.getenv('MODEL_TEMPERATURE', 0)))

class ClassificationState(TypedDict):
    pdf_file_path: str
    markdown_dict: dict
    agent_classification_result: dict
    hitl_decision: str
    document_id: str
    messages: Annotated[list, add_messages]
    audit_logs: Annotated[list[str], operator.add]
    classification: str
    error: Annotated[list[str], operator.add]

class ClassificationResult_Old(BaseModel):
    classification: Literal["CEASE", "UNCERTAIN", "IRRELEVANT"]
    confidence_score: int
    reasoning: str 
    key_phrases: list[str]
    urgency_level: str
    recommended_action: str

class ClassificationResult(BaseModel):
    classification:     Literal["CEASE", "UNCERTAIN", "IRRELEVANT"]
    confidence_score:   int = Field(ge=1, le=100)
    reasoning:          str
    key_phrases:        list[str]
    urgency_level:      Literal["HIGH", "MEDIUM", "LOW"]
    recommended_action: str

    @field_validator("confidence_score", mode="before")
    @classmethod
    def coerce_to_int(cls, v):
        return int(v)  # converts "100" → 100 silently


def pdf_to_markdown_tool(pdf_path: str) -> dict:
    """
    Convert a PDF (native or scanned) to Markdown.

    Args:
        pdf_path: Path to the input PDF.

    Returns:
        A dictionary with 'pages' (list of page dicts) and 'markdown' (str).
    """
    from pdf_to_markdown import pdf_to_markdown
    return pdf_to_markdown(pdf_path)

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _audit_entry(agent: str, message: str, color: str = "black") -> str:
    dict_colors = { "blue": "\033[94m", "green": "\033[92m", "yellow": "\033[93m", "red": "\033[91m", "endc": "\033[0m" }
    return f"[{_now()}] {dict_colors.get('green', '')}[{agent}]{dict_colors.get('endc', '')}{dict_colors.get(color, '')} {message}{dict_colors.get('endc', '')}"

def _init_db():
    conn = sqlite3.connect(os.getenv("SQL_LITE_DB_PATH"))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS classifications (
            document_id                TEXT PRIMARY KEY,
            document_text     TEXT,
            classification    TEXT,
            confidence_score  INTEGER,
            reasoning         TEXT,
            key_phrases       TEXT,
            pdf_file_path     TEXT,
            recommended_action TEXT,
            hitl_decision     TEXT,
            created_at        TEXT
        )
    """)
    conn.commit()
    conn.close()

def database_agent(state: ClassificationState) -> ClassificationState:
    print("[Database] Writing to SQLite...")
    try:
        _init_db()
        classification_result = state.get("agent_classification_result", {})
        conn = sqlite3.connect(os.getenv("SQL_LITE_DB_PATH"))
        conn.execute("""
            INSERT OR REPLACE INTO classifications VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            state["document_id"],
            state["markdown_dict"]["markdown"][:500],           # store first 500 chars
            state["classification"],
            getattr(classification_result, 'confidence_score', 0),
            getattr(classification_result, 'reasoning', ''),
            json.dumps(getattr(classification_result, 'key_phrases', [])),
            state["pdf_file_path"],
            getattr(classification_result, 'recommended_action', ''),
            state.get("hitl_decision", ""),
            _now()
        ))
        conn.commit()
        conn.close()
        log = _audit_entry("DATABASE", f"Saved document_id={state['document_id']} to SQLite.")
        print(f"[Database] Saved: {state['document_id']}")
        return {"audit_logs": [log]}
    except Exception as e:
        log = _audit_entry("DATABASE", f"ERROR: {str(e)}")
        return {"audit_logs": [log], "error": [str(e)]}

def audit_agent(state: ClassificationState) -> ClassificationState:
    print("[Audit] Writing audit trail...")
    classification_result = state.get("agent_classification_result", {})
    try:
        with open(os.getenv("AUDIT_LOG_PATH"), "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Document ID : {state['document_id']}\n")
            score = classification_result.confidence_score if hasattr(classification_result, 'confidence_score') else classification_result.get('confidence_score', 0)
            f.write(f"Final result: {state['classification']} (score={score})\n")
            f.write("Audit trail:\n")
            for entry in state.get("audit_logs", []):
                f.write(f"  {entry}\n")
        log = _audit_entry("AUDIT", f"Audit trail written for document_id={state['document_id']}")
        print(f"[Audit] Logged: {state['document_id']}")
        return {"audit_logs": [log]}
    except Exception as e:
        print(f"[Audit] ERROR: {e}")
        return {"audit_logs": [_audit_entry("AUDIT", f"ERROR: {str(e)}")]}

def manager_agent(state: ClassificationState) -> ClassificationState:
    logs = []
    logs.append(_audit_entry("MANAGER", f"Received document_id={state['document_id']}. Starting pipeline."))
    print(f"[Manager] Processing document: {state['document_id']}")
    markdown_dict = pdf_to_markdown_tool(state["pdf_file_path"])
    logs.append(_audit_entry("MANAGER", "Markdown Metadata: { PDF File Type: " + str(markdown_dict.get("mode", "N/A")) + ", extracted_pages=" + str(markdown_dict.get("extracted_pages", "N/A")) + "}"))
    logs.append(_audit_entry("MANAGER", "Completed PDF to Markdown conversion."))
    return {"markdown_dict": markdown_dict, "audit_logs": logs}

def classification_agent(state: ClassificationState) -> ClassificationState:
    try:
        logs = []
        logs.append(_audit_entry("CLASSIFICATION_AGENT", f"Starting classification for document_id={state['document_id']}"))
        print(f"[Classification Agent] Classifying document: {state['document_id']}")
        # Use structured output to get a Pydantic model back
        structured_llm = llm.with_structured_output(ClassificationResult)
        classification_result = structured_llm.invoke(
            [SystemMessage(content=CLASSIFY_PROMPT.format(document_text=state["markdown_dict"]["markdown"]))]
        )
        logs.append(_audit_entry("CLASSIFICATION_AGENT", 
                                f"\nClassification Category: {classification_result.classification}, \nConfidence Score: {classification_result.confidence_score} \nClassification Based on the Resoning: {classification_result.reasoning}".replace("\n", "\n" + " " * 20)))
        logs.append(_audit_entry("CLASSIFICATION_AGENT", "Completed classification.")) 
        return {"agent_classification_result": classification_result, "classification": classification_result.classification, "audit_logs": logs}
    except Exception as e:
        log = _audit_entry("CLASSIFICATION_AGENT", f"ERROR: {str(e)}")
        return {
            "classification": "UNCERTAIN",
            "confidence_score": 0,
            "reasoning": f"Classification failed: {str(e)}",
            "key_phrases": [],
            "urgency_level": "HIGH",
            "recommended_action": "Manual review required due to classification error.",
            "audit_log": [log],
            "error": str(e)
        }


def hitl_agent(state: ClassificationState) -> ClassificationState:
    """
    Pauses the graph and waits for a human decision.
    Resume by calling graph.invoke(Command(resume="CEASE"), config=config)
    Human can override with: CEASE, IRRELEVANT, or KEEP_UNCERTAIN
    """
    classification_result = state.get("agent_classification_result", {})
    print("\n[HITL]  Document requires human review.")
    print(f"  Reasoning : {getattr(classification_result, 'reasoning', 'N/A')}")
    print(f"  Score     : {getattr(classification_result, 'confidence_score', 0)}")
    print(f"  Phrases   : {getattr(classification_result, 'key_phrases', 'N/A')}")
    print("  Override options: CEASE | IRRELEVANT | KEEP_UNCERTAIN")

    human_decision = interrupt({
        "document_id":     state["document_id"],
        "classification":  state['classification'],
        "confidence_score": getattr(classification_result, 'confidence_score', 0),
        "reasoning":       getattr(classification_result, 'reasoning', 'N/A'),
        "key_phrases":     getattr(classification_result, 'key_phrases', 'N/A'),
        "prompt":          "Enter your decision: CEASE | IRRELEVANT | KEEP_UNCERTAIN"
    })

    valid = {"CEASE", "IRRELEVANT", "KEEP_UNCERTAIN"}
    decision = human_decision.strip().upper() if human_decision else "KEEP_UNCERTAIN"
    if decision not in valid:
        decision = "KEEP_UNCERTAIN"

    # Apply human override
    final_classification = getattr(classification_result, 'classification', 'N/A')
    if decision in {"CEASE", "IRRELEVANT"}:
        final_classification = decision

    log = _audit_entry("HITL", f"Human decision={decision} | Final={final_classification}")
    print(f"[HITL] Decision recorded: {decision}")

    return {
        "hitl_decision":  decision,
        "classification": final_classification,
        "audit_logs":      [log]
    }

def route_after_classification(state: ClassificationState) -> Literal["hitl_agent", "parallel_agents"]:
    if state["classification"] == "UNCERTAIN":
        return "hitl_agent"
    return "parallel_agents"

def archiving_agent(state: ClassificationState) -> ClassificationState:
    print("[Archiving] Writing to flat file...")
    ARCHIVE_PATH = os.getenv("ARCHIVE_PATH")
    classification_result = state.get("agent_classification_result", {})
    try:
        record = {
            "document_id":       state["document_id"],
            "classification":    state["classification"],
            "confidence_score":  getattr(classification_result, 'confidence_score', 0),
            "reasoning":         getattr(classification_result, 'reasoning', 'N/A'),
            "key_phrases":       getattr(classification_result, 'key_phrases', []),
            "pdf_file_path":     state["pdf_file_path"],
            #"recommended_action": state["recommended_action"],
            "hitl_decision":     state.get("hitl_decision", ""),
            "archived_at":       _now()
        }
        with open(ARCHIVE_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        log = _audit_entry("ARCHIVING", f"Appended document_id={state['document_id']} to {ARCHIVE_PATH}")
        print(f"[Archiving] Archived: {state['document_id']}")
        return {"audit_logs": [log]}
    except Exception as e:
        log = _audit_entry("ARCHIVING", f"ERROR: {str(e)}")
        return {"audit_logs": [log], "error": [str(e)]}

def resume_hitl(graph, thread_id: str, human_decision: str) -> dict:
    """Resume a paused UNCERTAIN pipeline after human review."""
    from langgraph.types import Command
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(Command(resume=human_decision), config=config)
    print(f"\n[Pipeline] ✅ Resumed & Complete — {result['classification']}")
    return {"status": "complete", "thread_id": thread_id, "state": result}

def build_graph():
    builder = StateGraph(ClassificationState)

    # Register nodes
    builder.add_node("manager_agent_",       manager_agent)
    builder.add_node("classification_agent_", classification_agent)
    builder.add_node("hitl_agent_",          hitl_agent)
    builder.add_node("database_agent_",      database_agent)
    builder.add_node("archiving_agent_",     archiving_agent)
    builder.add_node("audit_agent_",         audit_agent)

    # Entry edge
    builder.add_edge(START, "manager_agent_")
    builder.add_edge("manager_agent_", "classification_agent_")

    # Conditional: UNCERTAIN → HITL, else → parallel
    builder.add_conditional_edges(
        "classification_agent_",
        route_after_classification,
        {
            "hitl_agent":      "hitl_agent_",
            "parallel_agents": "database_agent_"      # LangGraph runs fan-outs via Send
        }
    )

    # After HITL → parallel agents
    builder.add_edge("hitl_agent_", "database_agent_")
    builder.add_edge("hitl_agent_", "archiving_agent_")

    # Parallel: DB + Archiving run together, both flow into Audit
    builder.add_edge("classification_agent_", "archiving_agent_")   # fan-out via duplicate edges
    builder.add_edge("database_agent_","audit_agent_")
    builder.add_edge("archiving_agent_","audit_agent_")
    builder.add_edge("audit_agent_",END)

    # MemorySaver enables HITL interrupt/resume
    memory = MemorySaver()
    return builder.compile(checkpointer=memory, interrupt_before=["hitl_agent_"])

def run_pipeline(pdf_file_path: str, document_id: str = None) -> dict:
    """
    Run the full pipeline.
    For UNCERTAIN documents, the graph will pause at hitl_agent.
    Call resume_hitl() with the thread_id and your decision to continue.
    """
    graph = build_graph()
    doc_id = document_id or f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    initial_state: ClassificationState = {
        "pdf_file_path":      pdf_file_path,
        "document_id":        doc_id
    }

    config = {"configurable": {"thread_id": doc_id}}
    result = graph.invoke(initial_state, config=config)

    if result.get("classification") == "UNCERTAIN" and not result.get("hitl_decision"):
        print(f"\n[Pipeline] ⏸ Paused for HITL review. thread_id={doc_id}")
        print("[Pipeline] Call resume_hitl(graph, doc_id, 'CEASE'|'IRRELEVANT'|'KEEP_UNCERTAIN') to continue.")
        return {"status": "paused", "thread_id": doc_id, "state": result}

    print(f"\n[Pipeline] ✅ Complete — {result.get('classification')} ")
    return {"status": "complete", "thread_id": doc_id, "state": result, "graph_res": graph}


import os
from datetime import datetime
from langgraph.types import Command

def get_next_doc_index(audit_log_path: str) -> int:
    """Reads audit log and returns the next document index."""
    if not os.path.exists(audit_log_path):
        return 1
    
    with open(audit_log_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    matches = re.findall(r"DOC-\d{14}-(\d{3})", content)
    
    if not matches:
        return 1
    
    return max(int(m) for m in matches) + 1

def process_folder(folder_path: str):
    """
    Loops all PDF files in a folder, runs the pipeline for each,
    and handles HITL pauses with user input before continuing.
    """
    pdf_files = sorted([
        f for f in os.listdir(folder_path)
        if f.lower().endswith(".pdf")
    ])

    if not pdf_files:
        print(f"No PDF files found in: {folder_path}")
        return

    print(f"Found {len(pdf_files)} PDF(s) to process.\n")

    for index, filename in enumerate(pdf_files, start=get_next_doc_index(os.getenv("AUDIT_LOG_PATH"))):
        pdf_path    = os.path.join(folder_path, filename)
        document_id = f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}-{index:03d}"

        print(f"\n{'='*60}")
        print(f"[{index}/{len(pdf_files)}] Processing : {filename}")
        print(f"             Document ID : {document_id}")
        print(f"{'='*60}")

        # ── Step 1: Run the pipeline ──────────────────────────────
        result = run_pipeline(pdf_path, document_id=document_id)

        # ── Step 2: Handle HITL pause ─────────────────────────────
        if result["status"] == "paused":
            classification_result = result["state"].get("agent_classification_result")

            print(f"\n⚠️  HITL Review Required for: {filename}")
            print(f"   Classification : {classification_result.classification}")
            print(f"   Confidence     : {classification_result.confidence_score}")
            print(f"   Reasoning      : {classification_result.reasoning}")
            print(f"   Key Phrases    : {classification_result.key_phrases}")
            print(f"\n   Options        : CEASE | IRRELEVANT | KEEP_UNCERTAIN")

            while True:
                human_decision = input("\n   Your decision: ").strip().upper()
                if human_decision in {"CEASE", "IRRELEVANT", "KEEP_UNCERTAIN"}:
                    break
                print("   ❌ Invalid input. Enter CEASE, IRRELEVANT, or KEEP_UNCERTAIN.")

            # ── Step 3: Resume graph after HITL decision ──────────
            config = {"configurable": {"thread_id": result["thread_id"]}}
            #resumed = resume_hitl(result.get("graph_res"), result["thread_id"], "CEASE")
            #resumed = graph.invoke(Command(resume=human_decision), config=config)
            print(f"\n✅ Resumed — Final: {result.get('classification')}")

        else:
            print(f"\n✅ Auto-classified — {result['state']['classification']}")

        print(f"   Done: {filename}\n")
        completed_folder = os.path.join(os.path.dirname(pdf_path), "Completed")
        os.makedirs(completed_folder, exist_ok=True)
        shutil.move(pdf_path, os.path.join(completed_folder, filename))

    print(f"\n{'='*60}")
    print(f"✅ All {len(pdf_files)} file(s) processed.")
    print(f"{'='*60}")


# ── Entry point ───────────────────────────────────────────────
if __name__ == "__main__":
    process_folder("Sample Docs")


""" # Older Logic
    # After HITL → parallel agents
    builder.add_edge("hitl_agent", "database_agent")
    builder.add_edge("hitl_agent", "archiving_agent")

    # Parallel: DB + Archiving run together, both flow into Audit
    builder.add_edge("classification_agent", "archiving_agent")   # fan-out via duplicate edges
    builder.add_edge("database_agent",        "audit_agent")
    builder.add_edge("archiving_agent",       "audit_agent")
    builder.add_edge("audit_agent",           END)

    # MemorySaver enables HITL interrupt/resume
    memory = MemorySaver()
    return builder.compile(checkpointer=memory, interrupt_before=["hitl_agent"])
build_graph = StateGraph(ClassificationState) \
    .add_node("MANAGER", manager_agent) \
    .add_node("CLASSIFY", clasification_agent) \
    .add_edge(START, "MANAGER") \
    .add_edge("MANAGER", "CLASSIFY") \
    .add_edge("CLASSIFY", END)
classification_agent = build_graph.compile()
# from IPython.display import Image, display
# display(Image(classification_agent.get_graph().draw_mermaid_png()))
if __name__ == "__main__":
    run_pipeline("Sample Docs\\bw_doc_1.pdf", document_id="DOC-CEASE-001")
    input(f"Final classification result: . Press Enter to exit.")
    agent_result = classification_agent.invoke({        "pdf_file_path": "Sample Docs\\bw_doc_1.pdf",        "document_id": f"DOC-{datetime.now().strftime('%Y%m%d%H%M%S')}",        })
    for log in agent_result['audit_logs']:
        print(log)
    input(f"Final classification result: {agent_result['agent_classification_result']}. Press Enter to exit.")
"""
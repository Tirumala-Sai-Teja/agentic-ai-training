"""
server.py — Cease & Desist Processor API  (v4)
------------------------------------------------
Two-phase HITL flow:
  Phase 1  POST /process        → classify docs; uncertain ones parked in memory
  Phase 2  POST /hitl-decision  → human submits decision; pipeline finalises

Endpoints:
  GET  /health        → health check
  POST /process       → upload + classify PDFs
  POST /hitl-decision → submit human decision for a parked doc
  GET  /hitl-pending  → list docs awaiting review
  GET  /results       → full audit log
  GET  /stats         → summary counts
"""

import os, sys, json, shutil, tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set WEB_MODE before importing the pipeline so hitl_agent never calls input()
os.environ["WEB_MODE"] = "1"

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from run_langgraph import (
    process_document,
    database_agent,
    archiving_agent,
    audit_agent,
)

AUDIT_FILE   = "audit_log.jsonl"
ARCHIVE_FILE = "irrelevant_documents.txt"
DB_PATH      = "cease_desist.db"

# In-memory store: document_name → full AgentState
pending_hitl: Dict[str, dict] = {}

app = FastAPI(title="C&D Processor", version="4.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── helpers ────────────────────────────────────────────────────────────────

def _is_hitl(state: dict) -> bool:
    """Return True if this document needs human review."""
    c = state.get("classification") or ""
    return c in ("hitl_needed", "uncertain")


def _state_to_response(state: dict, filename: str = "", hitl_pending: bool = False) -> dict:
    """Convert AgentState → clean JSON response for the frontend."""
    # Use classification directly — do NOT override hitl_needed with raw_class
    classification = state.get("human_decision") or state.get("classification") or "unknown"

    # Only show raw_class label after human has reviewed
    if not state.get("human_decision") and classification in ("hitl_needed", "uncertain"):
        display_class = "hitl_needed"
    else:
        display_class = classification

    return {
        "document_name":     state.get("document_name") or filename,
        "classification":    display_class,
        "confidence_score":  state.get("confidence_score") or 0,
        "reason":            state.get("classification_reason") or "",
        "irrelevant_reason": state.get("irrelevant_reason") or "",
        "sender_name":       state.get("extracted_details", {}).get("sender_name", "unknown"),
        "sender_address":    state.get("extracted_details", {}).get("sender_address", "unknown"),
        "cease_activity":    state.get("extracted_details", {}).get("cease_activity", "unknown"),
        "suggested":         state.get("extracted_details", {}).get("raw_class", "unknown"),
        "action_taken":      state.get("action_taken") or "",
        "human_reviewed":    bool(state.get("human_decision")),
        "hitl_pending":      hitl_pending,
        "processed_at":      datetime.now().isoformat(),
    }


# ── routes ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.post("/process")
async def process_files(files: List[UploadFile] = File(...)):
    """
    Phase 1 — Upload PDFs and classify.
    High-confidence docs are auto-processed.
    Low-confidence / uncertain docs are parked for HITL review.
    """
    if not files:
        raise HTTPException(400, "No files uploaded.")

    results, errors = [], []

    with tempfile.TemporaryDirectory() as tmpdir:
        for upload in files:
            if not upload.filename.lower().endswith(".pdf"):
                errors.append({"filename": upload.filename, "error": "Only PDFs supported."})
                continue

            tmp_path = os.path.join(tmpdir, upload.filename)
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(upload.file, f)

            try:
                state      = process_document(tmp_path, thread_id=Path(upload.filename).stem)
                needs_hitl = _is_hitl(state)

                if needs_hitl:
                    # Park the full state — human will complete it via /hitl-decision
                    pending_hitl[upload.filename] = state
                    print(f"[server] Parked '{upload.filename}' for HITL review")

                results.append(_state_to_response(state, upload.filename, hitl_pending=needs_hitl))

            except Exception as e:
                print(f"[server] Error processing '{upload.filename}': {e}")
                errors.append({"filename": upload.filename, "error": str(e)})

    return JSONResponse({
        "processed":     len(results),
        "errors":        len(errors),
        "results":       results,
        "error_details": errors,
    })


@app.post("/hitl-decision")
async def submit_hitl_decision(payload: dict):
    """
    Phase 2 — Human submits decision for a parked document.

    Body: { "document_name": "...", "decision": "cease|irrelevant", "reason": "..." }
    """
    doc_name = payload.get("document_name", "").strip()
    decision = payload.get("decision", "").strip().lower()
    reason   = payload.get("reason", "").strip()

    if not doc_name:
        raise HTTPException(400, "document_name is required.")
    if decision not in ("cease", "irrelevant"):
        raise HTTPException(400, "decision must be 'cease' or 'irrelevant'.")
    if doc_name not in pending_hitl:
        raise HTTPException(404, f"No pending HITL document: '{doc_name}'. It may have already been reviewed.")

    state = pending_hitl.pop(doc_name)

    # Apply human decision
    state["human_decision"]    = decision
    state["classification"]    = decision
    state["irrelevant_reason"] = reason if decision == "irrelevant" else state.get("irrelevant_reason", "")
    state["audit_log"]         = (state.get("audit_log") or []) + [{
        "agent":       "HITLAgent",
        "action":      f"Human decided: '{decision}' — {reason}",
        "timestamp":   datetime.now().isoformat(),
        "reviewed_by": "human_operator",
    }]

    # Resume pipeline
    try:
        if decision == "cease":
            updated = database_agent(state)
        else:
            updated = archiving_agent(state)

        # Merge updated fields back
        state.update(updated)
        audit_result = audit_agent(state)
        state.update(audit_result)

    except Exception as e:
        raise HTTPException(500, f"Pipeline error after HITL: {str(e)}")

    return JSONResponse(_state_to_response(state, doc_name, hitl_pending=False))


@app.get("/hitl-pending")
def get_pending():
    return {
        "count": len(pending_hitl),
        "documents": [
            {
                "document_name":    name,
                "suggested":        s.get("extracted_details", {}).get("raw_class", "unknown"),
                "confidence_score": s.get("confidence_score", 0),
                "reason":           s.get("classification_reason", ""),
                "preview":          (s.get("document_text") or "")[:400],
            }
            for name, s in pending_hitl.items()
        ],
    }


@app.get("/results")
def get_results():
    entries = []
    if Path(AUDIT_FILE).exists():
        with open(AUDIT_FILE) as f:
            for line in f:
                try: entries.append(json.loads(line.strip()))
                except: pass
    return {"total": len(entries), "results": entries}


@app.get("/stats")
def get_stats():
    counts = {"cease": 0, "irrelevant": 0, "uncertain": 0, "total": 0}
    if Path(AUDIT_FILE).exists():
        with open(AUDIT_FILE) as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    counts["total"] += 1
                    c = e.get("classification", "").lower()
                    if c == "cease":        counts["cease"]     += 1
                    elif c == "irrelevant": counts["irrelevant"] += 1
                    else:                   counts["uncertain"]  += 1
                except: pass
    counts["hitl_pending"] = len(pending_hitl)
    return counts


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8001, reload=False)
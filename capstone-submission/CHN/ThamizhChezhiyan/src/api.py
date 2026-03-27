from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import shutil
import uuid
import os
import signal
import logging

from src.config.config import DATA_DIR, LOGS_DIR, ARCHIVE_DIR
from src.database.models import init_db
from src.tools.document_loader import load_documents
from src.agents.audit_agent import AuditAgent
from src.agents.manager_agent import ManagerAgent
from src.agents.hitl_agent import HITLAgent

logger = logging.getLogger(__name__)

# Ensure data folders exist
for d in (DATA_DIR, LOGS_DIR, ARCHIVE_DIR):
    Path(d).mkdir(parents=True, exist_ok=True)

# Initialize database
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Database initialization failed: {e}")

app = FastAPI(
    title="EDPS Agentic Backend",
    description="FastAPI endpoints for Enterprise Document Processing System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"] ,
    allow_headers=["*"] ,
)

manager_agent = ManagerAgent()
hitl_agent = HITLAgent()
audit_agent = AuditAgent()


class ProcessFolderRequest(BaseModel):
    folder_path: str


class ReviewDecisionRequest(BaseModel):
    document_name: str
    human_decision: str
    reviewer_notes: Optional[str] = ""


@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "EDPS API is running"}


@app.post("/process/folder")
async def process_folder(request: ProcessFolderRequest):
    folder = Path(request.folder_path)
    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=404, detail="Folder not found")

    documents = load_documents(str(folder))
    if not documents:
        return {"status": "empty", "message": "No supported documents found", "documents": []}

    results = manager_agent.process_batch(documents)
    return {"status": "processed", "documents": len(documents), "results": results}


@app.post("/process/upload")
async def process_upload(file: UploadFile = File(...)):
    uploads_dir = Path(DATA_DIR) / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    saved_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = uploads_dir / saved_name

    try:
        with save_path.open("wb") as f:
            content = await file.read()
            f.write(content)

        result = manager_agent.process_document(str(save_path), file.filename)
        return {"status": "processed", "document": file.filename, "result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    status = manager_agent.get_system_status()
    return {"status": "ok", "system": status}


@app.get("/review/queue")
async def get_review_queue():
    queue = hitl_agent.get_review_queue()
    return {"status": "ok", "queue": queue}


@app.post("/review/decision")
async def submit_review(decision: ReviewDecisionRequest):
    success = hitl_agent.submit_review_decision(
        document_name=decision.document_name,
        human_decision=decision.human_decision,
        reviewer_notes=decision.reviewer_notes,
        database_agent=manager_agent.database_agent,
        archiving_agent=manager_agent.archiving_agent
    )

    if not success:
        raise HTTPException(status_code=500, detail="Could not record review decision")

    return {"status": "ok", "message": "Review decision captured"}


@app.get("/audit/logs")
async def get_audit_logs(limit: int = 50):
    """Get recent audit logs"""
    report = audit_agent.generate_audit_report()
    return {"status": "ok", "logs": report.get("recent_entries", []), "summary": report}


@app.post("/system/reset")
async def reset_system():
    """Reset system data (clear database, logs, archive)"""
    try:
        # Clear database - use correct database filename from config
        db_path = Path(DATA_DIR) / "edps.db"
        if db_path.exists():
            db_path.unlink()

        # Clear logs
        for log_file in Path(LOGS_DIR).glob("*.json"):
            log_file.unlink()

        # Clear archive
        archive_file = Path(ARCHIVE_DIR) / "irrelevant_documents.csv"
        if archive_file.exists():
            archive_file.unlink()

        # Clear uploads
        uploads_dir = Path(DATA_DIR) / "uploads"
        if uploads_dir.exists():
            shutil.rmtree(uploads_dir)
            uploads_dir.mkdir(parents=True, exist_ok=True)

        return {"status": "ok", "message": "System reset complete"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


@app.post("/system/shutdown")
async def shutdown_system():
    """Shutdown the backend service gracefully"""
    try:
        import threading, time

        def delayed_exit():
            time.sleep(0.2)
            # First ask uvicorn reload manager to stop too (parent process)
            parent_pid = os.getppid()
            if parent_pid and parent_pid != 1:
                try:
                    os.kill(parent_pid, signal.SIGINT)
                except Exception:
                    pass

            # Ensure this worker also exits
            os._exit(0)

        threading.Thread(target=delayed_exit, daemon=True).start()
        return {"status": "ok", "message": "Server shutdown initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shutdown failed: {str(e)}")

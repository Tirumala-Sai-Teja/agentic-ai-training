"""
FastAPI REST endpoint for Cease & Desist Document Processing System.
Optional REST API for cloud deployment and HTTP access.

Usage:
    OPENAI_API_KEY=sk-... uvicorn api:app --host 0.0.0.0 --port 8000
    
Or set API_ENABLE=true in .env and run main.py
"""
import logging
from typing import Optional
from datetime import datetime
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from graph.workflow import DocumentProcessingGraph
from models.db_models import init_db
from agents.database_agent import DatabaseAgent
from agents.audit_agent import AuditAgent
from config.settings import API_HOST, API_PORT

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cease & Desist Document Processor API",
    description="REST API for automated cease and desist document processing",
    version="1.0.0",
)

# Response schemas
class ProcessingResponse(BaseModel):
    """Response from document processing."""
    success: bool
    document_name: str
    classification: Optional[str]
    confidence: Optional[float]
    reasoning: Optional[str]
    sender_name: Optional[str]
    database_record_id: Optional[int]
    archive_record_id: Optional[int]
    error: Optional[str]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    version: str
    message: str


@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    logger.info("Initializing API...")
    init_db()
    logger.info("API initialized successfully")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(),
        version="1.0.0",
        message="Cease & Desist Processor is operational"
    )


@app.get("/api/v1/stats")
async def get_statistics():
    """Get system statistics."""
    try:
        audit_agent = AuditAgent()
        db_agent = DatabaseAgent()
        
        cease_records = db_agent.get_all_cease_records(limit=10000)
        summary = audit_agent.get_system_summary()
        
        return {
            "success": True,
            "cease_records_count": len(cease_records),
            "audit_stats": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/process", response_model=ProcessingResponse)
async def process_document(file: UploadFile = File(...)):
    """
    Process a cease and desist document.
    
    Args:
        file: PDF file to process
        
    Returns:
        ProcessingResponse with results
    """
    temp_path = None
    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="File must be a PDF")
        
        # Save uploaded file to temp location
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        
        document_name = file.filename or "document.pdf"
        
        # Process document
        graph = DocumentProcessingGraph()
        final_state = graph.process_document(temp_path, document_name)
        
        # Build response
        return ProcessingResponse(
            success=final_state.processing_status == "completed",
            document_name=document_name,
            classification=final_state.classification_result.classification if final_state.classification_result else None,
            confidence=final_state.classification_result.confidence if final_state.classification_result else None,
            reasoning=final_state.classification_result.reasoning if final_state.classification_result else None,
            sender_name=final_state.extraction_result.sender_name if final_state.extraction_result else None,
            database_record_id=final_state.database_record_id,
            archive_record_id=final_state.archive_record_id,
            error=final_state.error_message,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}", exc_info=True)
        return ProcessingResponse(
            success=False,
            document_name=file.filename or "unknown",
            classification=None,
            confidence=None,
            reasoning=None,
            sender_name=None,
            database_record_id=None,
            archive_record_id=None,
            error=str(e),
        )
    
    finally:
        # Clean up temp file
        if temp_path and Path(temp_path).exists():
            try:
                Path(temp_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {str(e)}")


@app.get("/api/v1/records")
async def get_cease_records(limit: int = 100):
    """Get all CEASE records."""
    try:
        db_agent = DatabaseAgent()
        records = db_agent.get_all_cease_records(limit=limit)
        
        return {
            "success": True,
            "count": len(records),
            "records": [
                {
                    "id": r.id,
                    "document_name": r.document_name,
                    "classification": r.classification,
                    "confidence": r.confidence,
                    "sender_name": r.extracted_details.get("sender_name") if r.extracted_details else None,
                    "received_date": r.received_date.isoformat(),
                }
                for r in records
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching records: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/audit/{document_name}")
async def get_document_audit(document_name: str):
    """Get audit trail for a specific document."""
    try:
        audit_agent = AuditAgent()
        logs = audit_agent.get_document_audit_trail(document_name)
        
        return {
            "success": True,
            "document_name": document_name,
            "audit_count": len(logs),
            "logs": logs,
        }
    except Exception as e:
        logger.error(f"Error fetching audit logs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info"
    )

"""
Pydantic schemas for data validation and type safety.
Defines all input/output models for the system.
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, Dict, Any
from datetime import datetime

# Classification Result
class ClassificationResult(BaseModel):
    """Result from the classification agent."""
    classification: Literal["CEASE", "UNCERTAIN", "IRRELEVANT"]
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "classification": "CEASE",
                "confidence": 0.95,
                "reasoning": "Document contains clear cease and desist language with legal threats."
            }
        }


# Extraction Result
class ExtractionResult(BaseModel):
    """Extracted fields from a CEASE document."""
    sender_name: Optional[str] = None
    sender_address: Optional[str] = None
    sender_email: Optional[str] = None
    sender_phone: Optional[str] = None
    request_date: Optional[str] = None
    intent_summary: str
    key_claims: list[str] = Field(default_factory=list)
    requested_actions: list[str] = Field(default_factory=list)
    deadline: Optional[str] = None
    legal_references: list[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "sender_name": "John Doe",
                "sender_address": "123 Legal Ave, Law City, LC 12345",
                "request_date": "2026-03-21",
                "intent_summary": "Cease use of trademarked logo",
                "key_claims": ["Trademark infringement"],
                "requested_actions": ["Remove logo from website", "Cease advertising"],
                "deadline": "2026-04-21"
            }
        }


# Ingestion Input
class DocumentIngestionInput(BaseModel):
    """Input for document ingestion."""
    document_path: str
    document_name: str
    source: str = "pdf_scanner"
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_path": "/path/to/cease_desist.pdf",
                "document_name": "cease_desist_001.pdf",
                "source": "pdf_scanner"
            }
        }


# Ingestion Output
class DocumentIngestionOutput(BaseModel):
    """Output from ingestion agent."""
    document_name: str
    extracted_text: str
    page_count: int
    file_size_bytes: int
    extraction_timestamp: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_name": "cease_desist_001.pdf",
                "extracted_text": "Dear Sir/Madam...",
                "page_count": 3,
                "file_size_bytes": 125000,
                "extraction_timestamp": "2026-03-21T10:30:00"
            }
        }


# Processing State (used in LangGraph workflow)
class ProcessingState(BaseModel):
    """Overall state of document processing."""
    document_name: str
    document_path: str
    extracted_text: str
    classification_result: Optional[ClassificationResult] = None
    extraction_result: Optional[ExtractionResult] = None
    database_record_id: Optional[int] = None
    archive_record_id: Optional[int] = None
    human_decision: Optional[Literal["CEASE", "UNCERTAIN", "IRRELEVANT"]] = None
    audit_logs: list[Dict[str, Any]] = Field(default_factory=list)
    processing_status: Literal["pending", "processing", "completed", "failed", "awaiting_human_review"] = "pending"
    error_message: Optional[str] = None
    received_date: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_name": "cease_desist_001.pdf",
                "document_path": "/path/to/cease_desist_001.pdf",
                "extracted_text": "Full text content...",
                "classification_result": {
                    "classification": "CEASE",
                    "confidence": 0.95,
                    "reasoning": "..."
                },
                "processing_status": "processing",
                "received_date": "2026-03-21T10:00:00"
            }
        }


# Database Record
class CeaseRecordCreate(BaseModel):
    """Schema for creating a CEASE record in database."""
    document_name: str
    received_date: datetime
    extracted_details: ExtractionResult
    classification: str
    reasoning: str
    confidence: float
    full_text: str
    
    class Config:
        from_attributes = True


# Archive Record
class ArchiveRecord(BaseModel):
    """Schema for archived documents."""
    document_name: str
    received_date: datetime
    classification: str
    extracted_text: Optional[str] = None
    archive_date: datetime = Field(default_factory=datetime.now)
    
    class Config:
        from_attributes = True


# HITL Request
class HITLRequest(BaseModel):
    """Human-in-the-loop review request."""
    document_name: str
    extracted_text: str
    initial_classification: str
    confidence: float
    reasoning: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_name": "uncertain_001.pdf",
                "extracted_text": "...",
                "initial_classification": "UNCERTAIN",
                "confidence": 0.55,
                "reasoning": "Document is ambiguous..."
            }
        }


# HITL Response
class HITLResponse(BaseModel):
    """Human decision for document classification."""
    human_decision: Literal["CEASE", "UNCERTAIN", "IRRELEVANT"]
    human_reasoning: str
    decision_timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "human_decision": "CEASE",
                "human_reasoning": "After careful review, this is definitely a cease and desist.",
                "decision_timestamp": "2026-03-21T10:45:00"
            }
        }


# Audit Log
class AuditLog(BaseModel):
    """Audit trail entry."""
    document_name: str
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str
    agent: str
    details: Dict[str, Any]
    status: Literal["success", "failure", "pending"] = "pending"
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "document_name": "cease_desist_001.pdf",
                "timestamp": "2026-03-21T10:30:00",
                "event_type": "classification",
                "agent": "ClassificationAgent",
                "details": {
                    "classification": "CEASE",
                    "confidence": 0.95
                },
                "status": "success"
            }
        }

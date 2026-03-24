"""
Database Agent - Stores CEASE records in SQLite database.
Handles persistence of classified and extracted documents.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from models.db_models import CeaseRecord, SessionLocal
from models.schemas import CeaseRecordCreate, ExtractionResult
from utils.logger import log_audit

logger = logging.getLogger(__name__)


class DatabaseAgent:
    """
    Agent responsible for storing CEASE records in database.
    
    Manages persistence of cease and desist documents and their extracted information.
    """
    
    def __init__(self):
        """Initialize the database agent."""
        self.name = "DatabaseAgent"
        logger.info(f"Initialized {self.name}")
    
    def store_cease_record(
        self,
        document_name: str,
        received_date: datetime,
        extraction_result: ExtractionResult,
        classification: str,
        reasoning: str,
        confidence: float,
        full_text: str,
    ) -> int:
        """
        Store a CEASE record in the database.
        
        Args:
            document_name: Name of the document
            received_date: Date document was received
            extraction_result: Extracted structured data
            classification: Classification result
            reasoning: Classification reasoning
            confidence: Confidence score
            full_text: Full text of the document
            
        Returns:
            ID of the created record
            
        Raises:
            SQLAlchemyError: If database operation fails
        """
        logger.info(f"[{self.name}] Storing CEASE record: {document_name}")
        
        # Add timestamp to document_name to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_document_name = f"{document_name}_{timestamp}"
        
        session = SessionLocal()
        try:
            # Create database record
            record = CeaseRecord(
                document_name=unique_document_name,
                received_date=received_date,
                extracted_details=extraction_result.model_dump(),
                classification=classification,
                reasoning=reasoning,
                confidence=confidence,
                full_text=full_text,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            record_id = record.id
            
            # Log audit
            log_audit(
                document_name=document_name,  # Use original name for audit log
                event_type="database_store",
                agent=self.name,
                status="success",
                details={
                    "record_id": record_id,
                    "classification": classification,
                    "confidence": confidence,
                    "stored_as": unique_document_name,
                }
            )
            
            logger.info(f"[{self.name}] Successfully stored record {record_id} for {document_name} (stored as {unique_document_name})")
            return record_id
        
        except SQLAlchemyError as e:
            session.rollback()
            error_msg = f"Database error while storing record: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="database_store",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise
        
        except Exception as e:
            session.rollback()
            error_msg = f"Unexpected error storing record: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="database_store",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise
        
        finally:
            session.close()
    
    def get_cease_record(self, document_name: str) -> Optional[CeaseRecord]:
        """
        Retrieve a CEASE record by document name.
        
        Args:
            document_name: Name of the document
            
        Returns:
            CeaseRecord if found, None otherwise
        """
        session = SessionLocal()
        try:
            record = session.query(CeaseRecord).filter(
                CeaseRecord.document_name == document_name
            ).first()
            return record
        finally:
            session.close()
    
    def get_all_cease_records(self, limit: int = 100) -> list[CeaseRecord]:
        """
        Retrieve all CEASE records.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of CeaseRecord instances
        """
        session = SessionLocal()
        try:
            records = session.query(CeaseRecord).limit(limit).all()
            return records
        finally:
            session.close()
    
    def update_cease_record(
        self,
        record_id: int,
        **kwargs
    ) -> CeaseRecord:
        """
        Update a CEASE record.
        
        Args:
            record_id: ID of the record to update
            **kwargs: Fields to update
            
        Returns:
            Updated CeaseRecord
        """
        session = SessionLocal()
        try:
            record = session.query(CeaseRecord).filter(CeaseRecord.id == record_id).first()
            if record:
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        setattr(record, key, value)
                session.commit()
            return record
        finally:
            session.close()
    
    def delete_cease_record(self, record_id: int) -> bool:
        """
        Delete a CEASE record.
        
        Args:
            record_id: ID of the record to delete
            
        Returns:
            True if deleted, False if not found
        """
        session = SessionLocal()
        try:
            record = session.query(CeaseRecord).filter(CeaseRecord.id == record_id).first()
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
        finally:
            session.close()
    
    def delete_all_cease_records(self) -> int:
        """
        Delete all CEASE records from the database.
        
        Returns:
            Number of records deleted
        """
        session = SessionLocal()
        try:
            count = session.query(CeaseRecord).delete()
            session.commit()
            logger.info(f"[{self.name}] Deleted {count} CEASE records")
            return count
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[{self.name}] Error deleting records: {str(e)}")
            raise
        finally:
            session.close()
    
    def count_cease_records(self) -> int:
        """
        Count total CEASE records in database.
        
        Returns:
            Number of CEASE records
        """
        session = SessionLocal()
        try:
            count = session.query(CeaseRecord).count()
            return count
        finally:
            session.close()

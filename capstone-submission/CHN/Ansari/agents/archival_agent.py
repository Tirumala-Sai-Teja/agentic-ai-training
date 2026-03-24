"""
Archival Agent - Archives IRRELEVANT documents to CSV and database.
Handles storage of documents that are not cease and desist letters.
"""
import csv
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError
from models.db_models import ArchiveRecord, SessionLocal
from config.settings import ARCHIVE_FILE
from utils.logger import log_audit

logger = logging.getLogger(__name__)


class ArchivalAgent:
    """
    Agent responsible for archiving IRRELEVANT documents.
    
    Stores non-cease-and-desist documents to both CSV and database.
    """
    
    def __init__(self):
        """Initialize the archival agent."""
        self.name = "ArchivalAgent"
        self.archive_file = ARCHIVE_FILE
        logger.info(f"Initialized {self.name}")
        
        # Initialize CSV if it doesn't exist
        self._init_archive_csv()
    
    def _init_archive_csv(self) -> None:
        """Initialize CSV file with headers if it doesn't exist."""
        if not self.archive_file.exists():
            try:
                with open(self.archive_file, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "document_name",
                        "received_date",
                        "classification",
                        "archive_date",
                        "extracted_text_preview"
                    ])
                logger.info(f"Initialized archive CSV file: {self.archive_file}")
            except IOError as e:
                logger.error(f"Failed to initialize archive CSV: {str(e)}")
                raise
    
    def archive_document(
        self,
        document_name: str,
        received_date: datetime,
        classification: str,
        extracted_text: str = None,
    ) -> int:
        """
        Archive an IRRELEVANT document.
        
        Args:
            document_name: Name of the document
            received_date: Date document was received
            classification: Classification result
            extracted_text: Optional extracted text
            
        Returns:
            ID of the created archive record
            
        Raises:
            Exception: If archival fails
        """
        logger.info(f"[{self.name}] Archiving document: {document_name}")
        
        # Add timestamp to document_name to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_document_name = f"{document_name}_{timestamp}"
        
        try:
            # Store in database
            database_record_id = self._archive_to_database(
                unique_document_name,
                received_date,
                classification,
                extracted_text,
            )
            
            # Store in CSV
            self._archive_to_csv(
                unique_document_name,
                received_date,
                classification,
                extracted_text,
            )
            
            # Log audit
            log_audit(
                document_name=document_name,  # Use original name for audit log
                event_type="archive",
                agent=self.name,
                status="success",
                details={
                    "record_id": database_record_id,
                    "classification": classification,
                }
            )
            
            logger.info(f"[{self.name}] Successfully archived {document_name} (stored as {unique_document_name})")
            return database_record_id
        
        except Exception as e:
            error_msg = f"Failed to archive document: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=document_name,
                event_type="archive",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise
    
    def _archive_to_database(
        self,
        document_name: str,
        received_date: datetime,
        classification: str,
        extracted_text: str = None,
    ) -> int:
        """
        Store archive record in database.
        
        Args:
            document_name: Name of the document
            received_date: Date document was received
            classification: Classification result
            extracted_text: Optional extracted text
            
        Returns:
            ID of the created record
        """
        session = SessionLocal()
        try:
            record = ArchiveRecord(
                document_name=document_name,
                received_date=received_date,
                classification=classification,
                extracted_text=extracted_text,
                csv_archived=0,
            )
            
            session.add(record)
            session.commit()
            session.refresh(record)
            
            # Mark as CSV archived if we succeed
            record.csv_archived = 1
            session.commit()
            
            return record.id
        
        except SQLAlchemyError as e:
            session.rollback()
            raise Exception(f"Database error during archive: {str(e)}")
        
        finally:
            session.close()
    
    def _archive_to_csv(
        self,
        document_name: str,
        received_date: datetime,
        classification: str,
        extracted_text: str = None,
    ) -> None:
        """
        Append archive record to CSV file.
        
        Args:
            document_name: Name of the document
            received_date: Date document was received
            classification: Classification result
            extracted_text: Optional extracted text
        """
        try:
            # Create text preview (first 200 chars)
            text_preview = ""
            if extracted_text:
                text_preview = extracted_text[:200].replace("\n", " ").replace('"', '""')
            
            with open(self.archive_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    document_name,
                    received_date.isoformat(),
                    classification,
                    datetime.now().isoformat(),
                    text_preview,
                ])
            
            logger.debug(f"Appended {document_name} to archive CSV")
        
        except IOError as e:
            raise Exception(f"Failed to write to archive CSV: {str(e)}")
    
    def get_archived_documents(self, limit: int = 100) -> list[dict]:
        """
        Retrieve archived documents from database.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of archived document records
        """
        session = SessionLocal()
        try:
            records = session.query(ArchiveRecord).limit(limit).all()
            return [
                {
                    "id": r.id,
                    "document_name": r.document_name,
                    "received_date": r.received_date,
                    "classification": r.classification,
                    "archive_date": r.archive_date,
                }
                for r in records
            ]
        finally:
            session.close()

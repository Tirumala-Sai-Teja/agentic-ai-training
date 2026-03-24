"""
Ingestion Agent - Handles PDF input and text extraction.
Responsible for reading documents and preparing them for classification.
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import logging

from services.pdf_service import PDFService, PDFExtractionError
from models.schemas import DocumentIngestionInput, DocumentIngestionOutput
from utils.logger import log_audit

logger = logging.getLogger(__name__)


class IngestionAgent:
    """
    Agent responsible for document ingestion and text extraction.
    
    Handles PDF input validation, text extraction, and text cleaning.
    """
    
    def __init__(self):
        """Initialize the ingestion agent."""
        self.name = "IngestionAgent"
        logger.info(f"Initialized {self.name}")
    
    def process(self, input_data: DocumentIngestionInput) -> DocumentIngestionOutput:
        """
        Process a document for ingestion.
        
        Args:
            input_data: Document ingestion input with file path
            
        Returns:
            DocumentIngestionOutput with extracted text
            
        Raises:
            PDFExtractionError: If PDF processing fails
        """
        logger.info(f"[{self.name}] Processing document: {input_data.document_name}")
        
        try:
            # Validate PDF
            PDFService.validate_pdf(input_data.document_path)
            logger.debug(f"PDF validation passed: {input_data.document_path}")
            
            # Extract text
            extracted_text, page_count = PDFService.extract_text(input_data.document_path)
            logger.info(f"Extracted text from {page_count} pages")
            
            # Get file info
            file_info = PDFService.get_file_info(input_data.document_path)
            file_size_bytes = file_info["file_size_bytes"]
            
            # Create output
            output = DocumentIngestionOutput(
                document_name=input_data.document_name,
                extracted_text=extracted_text,
                page_count=page_count,
                file_size_bytes=file_size_bytes,
                extraction_timestamp=datetime.now(),
            )
            
            # Log audit
            log_audit(
                document_name=input_data.document_name,
                event_type="ingestion",
                agent=self.name,
                status="success",
                details={
                    "pages": page_count,
                    "file_size_bytes": file_size_bytes,
                    "text_length": len(extracted_text),
                }
            )
            
            logger.info(f"[{self.name}] Successfully ingested {input_data.document_name}")
            return output
        
        except PDFExtractionError as e:
            logger.error(f"[{self.name}] PDF extraction failed: {str(e)}")
            log_audit(
                document_name=input_data.document_name,
                event_type="ingestion",
                agent=self.name,
                status="failure",
                details={"error": str(e)},
                error_message=str(e)
            )
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error during ingestion: {str(e)}"
            logger.error(f"[{self.name}] {error_msg}")
            log_audit(
                document_name=input_data.document_name,
                event_type="ingestion",
                agent=self.name,
                status="failure",
                details={"error": error_msg},
                error_message=error_msg
            )
            raise PDFExtractionError(error_msg) from e
    
    def validate_document(self, document_path: str) -> bool:
        """
        Validate that a document can be ingested.
        
        Args:
            document_path: Path to the document
            
        Returns:
            True if document is valid
        """
        try:
            PDFService.validate_pdf(document_path)
            return True
        except PDFExtractionError:
            return False

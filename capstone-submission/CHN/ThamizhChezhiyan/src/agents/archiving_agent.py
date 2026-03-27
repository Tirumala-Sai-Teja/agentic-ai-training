"""
Archiving Agent - Archives irrelevant documents to flat files
"""
import csv
from datetime import datetime
from pathlib import Path
from src.config.config import ARCHIVE_DIR
from src.tools.audit_logger import get_audit_trail
import logging
import time

logger = logging.getLogger(__name__)


class ArchivingAgent:
    """Agent responsible for archiving irrelevant documents"""

    def __init__(self, archive_file: Path = None):
        """
        Initialize the archiving agent
        
        Args:
            archive_file: Path to archive CSV file
        """
        self.archive_dir = ARCHIVE_DIR
        self.archive_dir.mkdir(exist_ok=True)
        self.archive_file = archive_file or (self.archive_dir / "irrelevant_documents.csv")
        self.audit_trail = get_audit_trail()
        self.name = "ArchivingAgent"
        self._init_archive_file()

    def _init_archive_file(self) -> None:
        """Initialize the archive CSV file if it doesn't exist"""
        if not self.archive_file.exists():
            try:
                with open(self.archive_file, 'w', newline='') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=['date_received', 'document_name', 'document_path', 'archived_at']
                    )
                    writer.writeheader()
                logger.info(f"Archive file initialized: {self.archive_file}")
            except Exception as e:
                logger.error(f"Error initializing archive file: {e}")
                raise

    def archive_document(
        self,
        document_name: str,
        document_path: str = None,
        date_received: datetime = None,
        max_retries: int = 3
    ) -> bool:
        """
        Archive an irrelevant document with retry logic
        
        Args:
            document_name: Name of the document
            document_path: Path to the document file
            date_received: Date the document was received
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if archived successfully, False otherwise
        """
        last_error = None
        for attempt in range(max_retries):
            try:
                if date_received is None:
                    date_received = datetime.utcnow()

                # Ensure archive file exists
                if not self.archive_file.exists():
                    with open(self.archive_file, 'w', newline='') as f:
                        writer = csv.DictWriter(
                            f,
                            fieldnames=['date_received', 'document_name', 'document_path', 'archived_at']
                        )
                        writer.writeheader()

                # Add record to archive file
                with open(self.archive_file, 'a', newline='') as f:
                    writer = csv.DictWriter(
                        f,
                        fieldnames=['date_received', 'document_name', 'document_path', 'archived_at']
                    )
                    writer.writerow({
                        'date_received': date_received.isoformat(),
                        'document_name': document_name,
                        'document_path': document_path or 'N/A',
                        'archived_at': datetime.utcnow().isoformat()
                    })

                # Log the action
                self.audit_trail.log_action(
                    agent_name=self.name,
                    action="Archive Document",
                    document_name=document_name,
                    explanation=f"Document archived to {self.archive_file}",
                    status="success"
                )

                logger.info(f"Document archived: {document_name}")
                return True

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Error archiving document {document_name}: {last_error}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff: 1, 2, 4 seconds
                    time.sleep(wait_time)
                continue
        
        # All retries exhausted
        logger.error(f"Failed to archive document {document_name} after {max_retries} attempts: {last_error}")
        self.audit_trail.log_action(
            agent_name=self.name,
            action="Archive Document",
            document_name=document_name,
            status="failed",
            explanation=f"Archiving error (retries exhausted): {last_error}"
        )
        return False

    def get_archived_documents(self) -> list:
        """
        Retrieve list of archived documents
        
        Returns:
            List of archived document records
        """
        archived = []
        try:
            with open(self.archive_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    archived.append(row)

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Retrieve Archived Documents",
                explanation=f"Retrieved {len(archived)} archived records",
                status="success"
            )

            logger.info(f"Retrieved {len(archived)} archived documents")
            return archived

        except Exception as e:
            logger.error(f"Error retrieving archived documents: {e}")
            return []

    def archive_batch(self, documents: list) -> int:
        """
        Archive multiple documents at once
        
        Args:
            documents: List of (document_name, document_path) tuples
        
        Returns:
            Number of successfully archived documents
        """
        archived_count = 0
        for doc_name, doc_path in documents:
            if self.archive_document(doc_name, doc_path):
                archived_count += 1

        self.audit_trail.log_action(
            agent_name=self.name,
            action="Archive Batch",
            explanation=f"Archived {archived_count}/{len(documents)} documents",
            status="success"
        )

        logger.info(f"Archived {archived_count}/{len(documents)} documents")
        return archived_count

    def get_archive_stats(self) -> dict:
        """
        Get statistics about archived documents
        
        Returns:
            Dictionary with archive statistics
        """
        try:
            archived = self.get_archived_documents()
            stats = {
                "total_archived": len(archived),
                "archive_file": str(self.archive_file)
            }

            self.audit_trail.log_action(
                agent_name=self.name,
                action="Get Archive Statistics",
                explanation=f"Archive stats: {stats}",
                status="success"
            )

            return stats

        except Exception as e:
            logger.error(f"Error getting archive statistics: {e}")
            return {"total_archived": 0, "error": str(e)}

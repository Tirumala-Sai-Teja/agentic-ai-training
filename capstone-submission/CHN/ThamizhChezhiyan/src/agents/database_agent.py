"""
Database Agent - Stores cease requests in the database
"""
from datetime import datetime
from sqlalchemy.orm import Session
from src.database.models import CeaseRequest, get_session
from src.tools.audit_logger import get_audit_trail
import logging
import time

logger = logging.getLogger(__name__)


class DatabaseAgent:
    """Agent responsible for storing processed documents in database"""

    def __init__(self):
        """Initialize the database agent"""
        self.audit_trail = get_audit_trail()
        self.name = "DatabaseAgent"

    def store_cease_request(
        self,
        document_name: str,
        classification: str,
        extracted_details: str,
        document_content_preview: str = None,
        customer_name: str = None,
        customer_id: str = None,
        processing_status: str = "pending",
        max_retries: int = 3
    ) -> bool:
        """
        Store a cease request in the database with retry logic
        
        Args:
            document_name: Name of the document
            classification: Classification result (Cease, Uncertain, Irrelevant)
            extracted_details: Extracted information from the document
            document_content_preview: Preview of document content
            customer_name: Name of the customer (if extracted)
            customer_id: ID of the customer (if extracted)
            processing_status: Status of processing
            max_retries: Maximum number of retry attempts
        
        Returns:
            True if stored successfully, False otherwise
        """
        last_error = None
        for attempt in range(max_retries):
            session = None
            try:
                session = get_session()
                
                # Create new cease request record
                cease_request = CeaseRequest(
                    document_name=document_name,
                    date_received=datetime.utcnow(),
                    classification=classification,
                    extracted_details=extracted_details,
                    document_content_preview=document_content_preview,
                    customer_name=customer_name,
                    customer_id=customer_id,
                    processing_status=processing_status
                )
                
                # Add to session and commit
                session.add(cease_request)
                session.commit()
                
                # Log the action
                self.audit_trail.log_action(
                    agent_name=self.name,
                    action="Store Cease Request",
                    document_name=document_name,
                    classification=classification,
                    explanation=f"Cease request stored with ID: {cease_request.id}",
                    status="success"
                )
                
                logger.info(f"Cease request stored: {document_name} (ID: {cease_request.id})")
                return True

            except Exception as e:
                if session:
                    try:
                        session.rollback()
                    except:
                        pass
                last_error = str(e)
                logger.warning(f"Attempt {attempt + 1}/{max_retries} - Error storing cease request {document_name}: {last_error}")
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt)  # Exponential backoff: 1, 2, 4 seconds
                    time.sleep(wait_time)
                continue
            finally:
                if session:
                    try:
                        session.close()
                    except:
                        pass
        
        # All retries exhausted
        logger.error(f"Failed to store cease request {document_name} after {max_retries} attempts: {last_error}")
        self.audit_trail.log_action(
            agent_name=self.name,
            action="Store Cease Request",
            document_name=document_name,
            status="failed",
            explanation=f"Storage error (retries exhausted): {last_error}"
        )
        return False

    def retrieve_cease_requests(self, classification: str = None) -> list:
        """
        Retrieve cease requests from database
        
        Args:
            classification: Optional filter by classification
        
        Returns:
            List of cease requests
        """
        session = None
        try:
            session = get_session()
            query = session.query(CeaseRequest)
            
            if classification:
                query = query.filter_by(classification=classification)
            
            results = query.all()
            
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Retrieve Cease Requests",
                explanation=f"Retrieved {len(results)} records",
                status="success"
            )
            
            return results

        except Exception as e:
            logger.error(f"Error retrieving cease requests: {e}")
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Retrieve Cease Requests",
                status="failed"
            )
            return []
        finally:
            if session:
                session.close()

    def update_processing_status(
        self,
        document_name: str,
        new_status: str
    ) -> bool:
        """
        Update the processing status of a document
        
        Args:
            document_name: Name of the document
            new_status: New processing status
        
        Returns:
            True if updated successfully, False otherwise
        """
        session = None
        try:
            session = get_session()
            
            cease_request = session.query(CeaseRequest).filter_by(
                document_name=document_name
            ).first()
            
            if cease_request:
                cease_request.processing_status = new_status
                cease_request.updated_at = datetime.utcnow()
                session.commit()
                
                self.audit_trail.log_action(
                    agent_name=self.name,
                    action="Update Processing Status",
                    document_name=document_name,
                    explanation=f"Status updated to: {new_status}",
                    status="success"
                )
                
                logger.info(f"Updated status for {document_name} to {new_status}")
                return True
            else:
                logger.warning(f"Document {document_name} not found in database")
                return False

        except Exception as e:
            if session:
                session.rollback()
            logger.error(f"Error updating processing status: {e}")
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Update Processing Status",
                status="failed"
            )
            return False
        finally:
            if session:
                session.close()

    def get_document_stats(self) -> dict:
        """
        Get statistics about stored cease requests
        
        Returns:
            Dictionary with statistics
        """
        session = None
        try:
            session = get_session()
            
            total = session.query(CeaseRequest).count()
            cease_count = session.query(CeaseRequest).filter_by(
                classification="Cease"
            ).count()
            uncertain_count = session.query(CeaseRequest).filter_by(
                classification="Uncertain"
            ).count()
            irrelevant_count = session.query(CeaseRequest).filter_by(
                classification="Irrelevant"
            ).count()
            
            stats = {
                "total_documents": total,
                "cease_requests": cease_count,
                "uncertain_documents": uncertain_count,
                "irrelevant_documents": irrelevant_count
            }
            
            self.audit_trail.log_action(
                agent_name=self.name,
                action="Get Statistics",
                explanation=f"Stats: {stats}",
                status="success"
            )
            
            return stats

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
        finally:
            if session:
                session.close()

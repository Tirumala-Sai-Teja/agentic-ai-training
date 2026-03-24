"""
Audit Agent - Comprehensive audit logging system.
Tracks all operations, decisions, and events throughout the document processing pipeline.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy.exc import SQLAlchemyError
from models.db_models import AuditLogEntry, SessionLocal
from config.settings import AUDIT_ENABLED, AUDIT_LOG_DATABASE
from utils.logger import audit_logger

logger = logging.getLogger(__name__)


class AuditAgent:
    """
    Agent responsible for comprehensive audit logging.
    
    Maintains detailed audit trail of all system operations for compliance and debugging.
    """
    
    def __init__(self):
        """Initialize the audit agent."""
        self.name = "AuditAgent"
        self.enabled = AUDIT_ENABLED
        self.log_to_database = AUDIT_LOG_DATABASE
        logger.info(f"Initialized {self.name} (enabled={self.enabled}, db_logging={self.log_to_database})")
    
    def log_event(
        self,
        document_name: str,
        event_type: str,
        agent: str,
        details: Dict[str, Any],
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> Optional[int]:
        """
        Log an audit event.
        
        Args:
            document_name: Name of document being processed
            event_type: Type of event (classification, extraction, etc.)
            agent: Name of agent that performed action
            details: Dictionary with event-specific details
            status: Status of event (success, failure, pending)
            error_message: Optional error message if status is failure
            
        Returns:
            Audit log record ID if database logging is enabled, None otherwise
        """
        if not self.enabled:
            return None
        
        timestamp = datetime.now()
        
        # Log to file
        self._log_to_file(
            document_name,
            timestamp,
            event_type,
            agent,
            details,
            status,
            error_message,
        )
        
        # Log to database if enabled
        if self.log_to_database:
            return self._log_to_database(
                document_name,
                timestamp,
                event_type,
                agent,
                details,
                status,
                error_message,
            )
        
        return None
    
    def _log_to_file(
        self,
        document_name: str,
        timestamp: datetime,
        event_type: str,
        agent: str,
        details: Dict[str, Any],
        status: str,
        error_message: Optional[str],
    ) -> None:
        """
        Log event to audit file.
        
        Args:
            document_name: Document name
            timestamp: Event timestamp
            event_type: Type of event
            agent: Agent name
            details: Event details
            status: Event status
            error_message: Optional error message
        """
        try:
            log_message = f"[{timestamp.isoformat()}] [{status.upper()}] [{agent}] {event_type} on {document_name}"
            
            if error_message:
                log_message += f" - ERROR: {error_message}"
            
            audit_logger.info(log_message)
            
            # Log details as structured data
            details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
            if details_str:
                audit_logger.debug(f"Details: {details_str}")
        
        except Exception as e:
            logger.error(f"Error logging to audit file: {str(e)}")
    
    def _log_to_database(
        self,
        document_name: str,
        timestamp: datetime,
        event_type: str,
        agent: str,
        details: Dict[str, Any],
        status: str,
        error_message: Optional[str],
    ) -> Optional[int]:
        """
        Log event to audit database table.
        
        Args:
            document_name: Document name
            timestamp: Event timestamp
            event_type: Type of event
            agent: Agent name
            details: Event details
            status: Event status
            error_message: Optional error message
            
        Returns:
            Audit log record ID if successful, None otherwise
        """
        session = SessionLocal()
        try:
            log_entry = AuditLogEntry(
                document_name=document_name,
                timestamp=timestamp,
                event_type=event_type,
                agent=agent,
                details=details,
                status=status,
                error_message=error_message,
            )
            
            session.add(log_entry)
            session.commit()
            session.refresh(log_entry)
            
            return log_entry.id
        
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error while logging audit event: {str(e)}")
            return None
        
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error while logging audit event: {str(e)}")
            return None
        
        finally:
            session.close()
    
    def get_audit_logs(
        self,
        document_name: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[Dict[str, Any]]:
        """
        Retrieve audit logs from database.
        
        Args:
            document_name: Optional filter by document name
            event_type: Optional filter by event type
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
        """
        if not self.log_to_database:
            logger.warning("Database logging is not enabled")
            return []
        
        session = SessionLocal()
        try:
            query = session.query(AuditLogEntry)
            
            if document_name:
                query = query.filter(AuditLogEntry.document_name == document_name)
            
            if event_type:
                query = query.filter(AuditLogEntry.event_type == event_type)
            
            logs = query.order_by(AuditLogEntry.timestamp.desc()).limit(limit).all()
            
            return [
                {
                    "id": log.id,
                    "document_name": log.document_name,
                    "timestamp": log.timestamp.isoformat(),
                    "event_type": log.event_type,
                    "agent": log.agent,
                    "status": log.status,
                    "details": log.details,
                    "error_message": log.error_message,
                }
                for log in logs
            ]
        
        finally:
            session.close()
    
    def get_document_audit_trail(self, document_name: str) -> list[Dict[str, Any]]:
        """
        Get complete audit trail for a specific document.
        
        Args:
            document_name: Name of the document
            
        Returns:
            Ordered list of audit events for the document
        """
        return self.get_audit_logs(
            document_name=document_name,
            limit=1000,
        )
    
    def get_system_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics of system audit logs.
        
        Returns:
            Dictionary with audit summary statistics
        """
        if not self.log_to_database:
            return {"error": "Database logging not enabled"}
        
        session = SessionLocal()
        try:
            total_logs = session.query(AuditLogEntry).count()
            successful_logs = session.query(AuditLogEntry).filter(
                AuditLogEntry.status == "success"
            ).count()
            failed_logs = session.query(AuditLogEntry).filter(
                AuditLogEntry.status == "failure"
            ).count()
            pending_logs = session.query(AuditLogEntry).filter(
                AuditLogEntry.status == "pending"
            ).count()
            
            event_types = session.query(AuditLogEntry.event_type).distinct().all()
            event_type_list = [e[0] for e in event_types]
            
            return {
                "total_logs": total_logs,
                "successful_logs": successful_logs,
                "failed_logs": failed_logs,
                "pending_logs": pending_logs,
                "event_types": event_type_list,
            }
        
        finally:
            session.close()

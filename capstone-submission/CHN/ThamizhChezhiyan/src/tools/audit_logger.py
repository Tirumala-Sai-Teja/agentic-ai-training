"""
Audit logging utility module
"""
import logging
import json
from datetime import datetime
from pathlib import Path
from pythonjsonlogger import jsonlogger
from src.config.config import LOGS_DIR, AUDIT_LOG_FILE


def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with JSON formatting for audit trail
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # File handler with JSON formatter
    LOGS_DIR.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(LOGS_DIR / f"{name}.log")
    json_formatter = jsonlogger.JsonFormatter()
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


class AuditTrail:
    """Manage audit trail for compliance and tracking"""

    def __init__(self):
        """Initialize audit trail"""
        self.audit_file = AUDIT_LOG_FILE
        self.audit_file.parent.mkdir(exist_ok=True)
        self.logger = setup_logger("audit_trail")

    def log_action(
        self,
        agent_name: str,
        action: str,
        document_name: str = None,
        classification: str = None,
        explanation: str = None,
        status: str = "success"
    ) -> None:
        """
        Log an action in the audit trail
        
        Args:
            agent_name: Name of the agent performing the action
            action: Description of the action
            document_name: Name of the document being processed
            classification: Classification result
            explanation: Detailed explanation for the action
            status: Status of the action (success, failed, review_required)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent_name": agent_name,
            "action": action,
            "document_name": document_name,
            "classification": classification,
            "explanation": explanation,
            "status": status
        }

        # Log to file
        with open(self.audit_file, 'a') as f:
            f.write(json.dumps(log_entry) + "\n")

        # Log to logger
        self.logger.info(
            f"Agent: {agent_name} | Action: {action} | Document: {document_name} | Status: {status}",
            extra=log_entry
        )

    def get_audit_trail(self, document_name: str = None) -> list:
        """
        Retrieve audit trail for a specific document or all documents
        
        Args:
            document_name: Optional document name to filter
        
        Returns:
            List of audit log entries
        """
        entries = []
        try:
            if self.audit_file.exists():
                with open(self.audit_file, 'r') as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        if document_name is None or entry.get("document_name") == document_name:
                            entries.append(entry)
        except Exception as e:
            self.logger.error(f"Error retrieving audit trail: {e}")

        return entries


# Global audit trail instance
_audit_trail = None


def get_audit_trail() -> AuditTrail:
    """Get or create audit trail instance"""
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail()
    return _audit_trail

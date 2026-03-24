"""
Logging configuration and utilities.
Sets up file and console logging for the system.
"""
import logging
import logging.handlers
from pathlib import Path
from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, AUDIT_LOG_FILE

# Create logs directory if needed
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def setup_logger(
    name: str,
    log_file: Path,
    level: str = LOG_LEVEL,
    log_format: str = LOG_FORMAT,
) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file
        level: Logging level
        log_format: Log format string
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Only add handlers if not already present
    if not logger.handlers:
        # Create formatter
        formatter = logging.Formatter(log_format)
        
        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


# Main application logger
main_logger = setup_logger("cease_desist_system", LOG_FILE)

# Audit logger
audit_logger = setup_logger("cease_desist_system.audit", AUDIT_LOG_FILE)


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_audit(
    document_name: str,
    event_type: str,
    agent: str,
    status: str,
    details: dict,
    error_message: str = None,
) -> None:
    """
    Log an audit event.
    
    Args:
        document_name: Name of document being processed
        event_type: Type of event (classification, extraction, etc.)
        agent: Name of agent that performed action
        status: Status (success, failure, pending)
        details: Dictionary with event details
        error_message: Optional error message
    """
    log_message = f"[{agent}] {event_type}: {document_name} - Status: {status}"
    
    if error_message:
        log_message += f" - Error: {error_message}"
    
    audit_logger.info(log_message)
    
    # Also log details as JSON-like structure
    details_str = " | ".join([f"{k}={v}" for k, v in details.items()])
    audit_logger.debug(f"Details: {details_str}")

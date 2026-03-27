"""
Database models for EDPS system
"""
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.config.config import DATABASE_URL
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class CeaseRequest(Base):
    """Model for Cease & Desist requests"""
    __tablename__ = "cease_requests"

    id = Column(Integer, primary_key=True)
    document_name = Column(String(255), nullable=False)
    date_received = Column(DateTime, default=datetime.utcnow)
    classification = Column(String(50), nullable=False)  # Cease, Uncertain, Irrelevant
    extracted_details = Column(Text, nullable=True)
    customer_name = Column(String(255), nullable=True)
    customer_id = Column(String(255), nullable=True)
    document_content_preview = Column(Text, nullable=True)
    processing_status = Column(String(50), default="pending")  # pending, processed, manual_review
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<CeaseRequest(id={self.id}, document_name={self.document_name}, classification={self.classification})>"


class AuditLog(Base):
    """Model for audit logging"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    agent_name = Column(String(100), nullable=False)
    action = Column(String(255), nullable=False)
    document_name = Column(String(255), nullable=True)
    classification = Column(String(50), nullable=True)
    explanation = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)  # success, failed, review_required

    def __repr__(self):
        return f"<AuditLog(id={self.id}, agent={self.agent_name}, action={self.action}, status={self.status})>"


# Database initialization and connection pooling
_engine = None
_Session = None


def get_engine():
    """Get or create database engine with proper SQLite configuration"""
    global _engine
    if _engine is None:
        # SQLite optimizations for concurrent access
        connect_args = {
            'timeout': 30,  # 30 second timeout for database locks
            'check_same_thread': False,
        }
        
        engine_kwargs = {
            'connect_args': connect_args,
            'echo': False,
            'pool_pre_ping': True,  # Verify connections before using
            'pool_recycle': 3600,  # Recycle connections after 1 hour
        }
        
        # Use NullPool for SQLite to avoid connection pooling issues
        if 'sqlite' in DATABASE_URL.lower():
            engine_kwargs['poolclass'] = StaticPool
        
        _engine = create_engine(DATABASE_URL, **engine_kwargs)
        
        # Enable WAL mode for SQLite (better concurrency)
        if 'sqlite' in DATABASE_URL.lower():
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                try:
                    cursor = dbapi_connection.cursor()
                    # Enable Write-Ahead Logging for better concurrent access
                    cursor.execute("PRAGMA journal_mode=WAL")
                    # Increase timeout
                    cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
                    # Synchronous mode for better performance during high load
                    cursor.execute("PRAGMA synchronous=NORMAL")
                    cursor.close()
                    logger.debug("SQLite pragmas configured: WAL mode enabled")
                except Exception as e:
                    logger.warning(f"Could not configure SQLite pragmas: {e}")
    
    return _engine


def init_db():
    """Initialize database and create tables"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database initialized successfully")
    return engine


def get_session():
    """Get database session with connection pooling"""
    global _Session
    if _Session is None:
        engine = get_engine()
        _Session = sessionmaker(bind=engine)
    
    return _Session()

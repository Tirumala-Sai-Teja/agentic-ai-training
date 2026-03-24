"""
SQLAlchemy ORM models for database tables.
Manages persistent storage for CEASE records and audit logs.
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config.settings import DATABASE_URL, SQLALCHEMY_ECHO
from typing import Optional

Base = declarative_base()


class CeaseRecord(Base):
    """
    Database model for CEASE & Desist records.
    Stores processed cease and desist documents.
    """
    __tablename__ = "cease_records"
    
    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String(255), unique=True, nullable=False, index=True)
    received_date = Column(DateTime, nullable=False, index=True)
    extracted_details = Column(JSON, nullable=False)  # Stores ExtractionResult
    classification = Column(String(50), nullable=False, index=True)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    full_text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self) -> str:
        return f"<CeaseRecord(id={self.id}, document_name='{self.document_name}', classification='{self.classification}')>"


class AuditLogEntry(Base):
    """
    Database model for audit logs.
    Tracks all operations and decisions made by agents.
    """
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.now)
    event_type = Column(String(100), nullable=False, index=True)
    agent = Column(String(100), nullable=False)
    details = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="pending")  # success, failure, pending
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self) -> str:
        return f"<AuditLogEntry(id={self.id}, document_name='{self.document_name}', event_type='{self.event_type}', status='{self.status}')>"


class ArchiveRecord(Base):
    """
    Database model for archived documents.
    Stores metadata about documents that were classified as IRRELEVANT.
    """
    __tablename__ = "archive_records"
    
    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String(255), unique=True, nullable=False, index=True)
    received_date = Column(DateTime, nullable=False, index=True)
    classification = Column(String(50), nullable=False)
    extracted_text = Column(Text, nullable=True)
    archive_date = Column(DateTime, nullable=False, default=datetime.now)
    csv_archived = Column(Integer, default=0)  # 1 if also backed up to CSV
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    
    def __repr__(self) -> str:
        return f"<ArchiveRecord(id={self.id}, document_name='{self.document_name}')>"


# Database initialization
def init_db() -> None:
    """Initialize database tables."""
    engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)
    Base.metadata.create_all(bind=engine)


def get_session():
    """
    Get a database session.
    Use as context manager or with dependency injection.
    """
    engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# Session factory for use in agents
engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

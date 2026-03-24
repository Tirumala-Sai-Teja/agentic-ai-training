"""
Configuration settings for the Cease & Desist Document Processing System.
Handles environment variables, database paths, LLM settings, and logging configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal

# Load environment variables from .env file
load_dotenv()

# Project root and paths
PROJECT_ROOT = Path(__file__).parent.parent
STORAGE_DIR = PROJECT_ROOT / "storage"
LOGS_DIR = STORAGE_DIR / "logs"
DATABASE_PATH = STORAGE_DIR / "database.db"
ARCHIVE_FILE = STORAGE_DIR / "archive.csv"

# Ensure storage directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
LLM_PROVIDER: Literal["openai", "groq", "mock"] = os.getenv("LLM_PROVIDER", "groq").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_RETRY_ATTEMPTS = int(os.getenv("LLM_RETRY_ATTEMPTS", "3"))

# Database Configuration
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_FILE = LOGS_DIR / "system.log"
AUDIT_LOG_FILE = LOGS_DIR / "audit.log"

# Processing Configuration
PDF_EXTRACTION_METHOD = os.getenv("PDF_EXTRACTION_METHOD", "pdfplumber")
TEMP_PDF_DIR = STORAGE_DIR / "temp_pdfs"
MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "50"))

# Classification Configuration
CLASSIFICATION_CONFIDENCE_THRESHOLD = float(os.getenv("CLASSIFICATION_CONFIDENCE_THRESHOLD", "0.7"))
ALLOWED_CLASSIFICATIONS = ["CEASE", "UNCERTAIN", "IRRELEVANT"]

# HITL Configuration
HITL_TIMEOUT = int(os.getenv("HITL_TIMEOUT", "300"))  # 5 minutes
HITL_MAX_RETRIES = int(os.getenv("HITL_MAX_RETRIES", "3"))

# API Configuration (for FastAPI endpoint)
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_ENABLE = os.getenv("API_ENABLE", "false").lower() == "true"

# Mock mode for testing without OpenAI API
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() == "true"

# Audit Configuration
AUDIT_ENABLED = os.getenv("AUDIT_ENABLED", "true").lower() == "true"
AUDIT_LOG_DATABASE = os.getenv("AUDIT_LOG_DATABASE", "true").lower() == "true"

# Ensure temp directory exists
TEMP_PDF_DIR.mkdir(parents=True, exist_ok=True)

# Validate critical settings
if not MOCK_MODE:
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required when LLM_PROVIDER is 'openai' "
                "and MOCK_MODE is disabled. Get one from https://platform.openai.com/api-keys"
            )
    elif LLM_PROVIDER == "groq":
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY environment variable is required when LLM_PROVIDER is 'groq' "
                "and MOCK_MODE is disabled. Get one from https://console.groq.com"
            )
    elif LLM_PROVIDER != "mock":
        raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}. Use 'openai', 'groq', or 'mock'")

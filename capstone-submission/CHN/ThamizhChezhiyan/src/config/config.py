"""
Configuration module for EDPS system
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
ARCHIVE_DIR = BASE_DIR / "archive"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
ARCHIVE_DIR.mkdir(exist_ok=True)

# Database configuration
DATABASE_URL = f"sqlite:///{DATA_DIR / 'edps.db'}"
DATABASE_PATH = DATA_DIR / "edps.db"

# LLM Configuration

# Try automatically loading .env if present (and if python-dotenv is installed)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads from .env in the working directory
except Exception:
    # Fallback: manual .env parsing
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key not in os.environ:
                            os.environ[key] = val
        except Exception as _:
            pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

# Document Processing
SUPPORTED_FORMATS = {".pdf", ".txt", ".png", ".jpg", ".jpeg"}
OCR_ENABLED = True
OCR_DPI = int(os.getenv("OCR_DPI", "70"))
OCR_LANG = os.getenv("OCR_LANG", "en")
OCR_USE_GPU = os.getenv("OCR_USE_GPU", "False").lower() in ["1", "true", "yes", "on"]

# Classification Categories
CLASSIFICATION_CATEGORIES = {
    "Cease": "Valid cease & desist request",
    "Uncertain": "Requires manual review",
    "Irrelevant": "Not a cease request"
}

# File paths for archiving
IRRELEVANT_FILE = ARCHIVE_DIR / "irrelevant_documents.csv"
AUDIT_LOG_FILE = LOGS_DIR / "audit_log.json"

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
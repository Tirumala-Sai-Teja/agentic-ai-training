# Cease & Desist Document Processing System

A Python system using **LangChain** and **LangGraph** for automated classification, extraction, and processing of Cease & Desist documents.

## 🎯 Overview

This system automatically:
- **Classifies** documents into CEASE, UNCERTAIN, or IRRELEVANT categories
- **Extracts** structured information (sender, date, claims, actions) from CEASE letters
- **Routes** documents to appropriate handlers (database, archive, human review)
- **Logs** comprehensive audit trails for compliance
- **Supports** human-in-the-loop review for uncertain documents

## 📋 Architecture

### Multi-Agent System

```
┌──────────────────────────────────────────────────────────────┐
│        CEASE & DESIST DOCUMENT PROCESSING WORKFLOW           │
└──────────────────────────────────────────────────────────────┘

                        ┌─────────────┐
                        │   START     │
                        └──────┬──────┘
                               │
                        ┌──────▼──────┐
                        │  INGESTION  │ (Extract text from PDF)
                        └──────┬──────┘
                               │
                        ┌──────▼────────────┐
                        │ CLASSIFICATION   │ (Classify document)
                        └──────┬──────────▬─┘
                               │          │
                        ┌──────┴────┬─────┴──────┬──────────┐
                        │           │            │          │
                   CEASE ▼      IRRELEVANT▼    UNCERTAIN▼  ERROR
                        │           │            │          │
         ┌──────────┐   │ ┌──────┐  │ ┌───────┐│ │
         │EXTRACTION│   │ │ARCHIVE   │ │HITL  ││ │
         └────┬─────┘   │ └───┬──────┘ └────┬─┘│ │
              │         │     │             │  │ │
         ┌────▼──────┐  │     │         ┌───▼──┴─┘
         │ DATABASE  │  │     │         │ (after decision)
         └────┬──────┘  │     │         │
              │         │    ◄┴────────┘
              │    ┌────┴─────┐
              │    │  ARCHIVE  │
              │    └────┬──────┘
              │         │
              └────┬────┘
                   │
            ┌──────▼──────┐
            │   AUDIT     │ (Log all operations)
            └──────┬──────┘
                   │
            ┌──────▼──────┐
            │     END     │
            └─────────────┘
```

### Agent Architecture

```
agents/
├── ingestion_agent.py      - PDF text extraction
├── classification_agent.py  - LLM-based classification
├── extraction_agent.py      - Structured data extraction
├── database_agent.py        - SQLite persistence
├── archival_agent.py        - CSV + DB archival
├── hitl_agent.py            - Human-in-the-loop review
└── audit_agent.py           - Comprehensive audit logging

services/
├── pdf_service.py           - PDF processing (pdfplumber, PyPDF2, OCR)
└── llm_service.py           - LLM interface (OpenAI, Groq, Mock)

graph/
└── workflow.py              - LangGraph orchestration
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to project
cd cease_desist_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file in project root:

```bash
# LLM Configuration (Choose ONE provider)
LLM_PROVIDER=groq            # Options: groq (recommended), openai, mock

# For Groq (FREE, no credit card needed!) - RECOMMENDED
GROQ_API_KEY=your-groq-key   # Get from https://console.groq.com
GROQ_MODEL=llama-3.1-8b-instant

# For OpenAI (Alternative)
OPENAI_API_KEY=sk-...        # Your OpenAI API key
OPENAI_MODEL=gpt-4-turbo-preview

# Settings
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000

# Mock Mode (for testing without any API key)
MOCK_MODE=false              # Set to true for offline testing

# Logging
LOG_LEVEL=INFO
AUDIT_ENABLED=true
AUDIT_LOG_DATABASE=true

# Database
DATABASE_PATH=storage/database.db

# API Server (optional)
API_ENABLE=false
API_PORT=8000
```

### 3. Initialize Database

```bash
python -c "from models.db_models import init_db; init_db(); print('Database initialized!')"
```

### 4. Run the System

```bash
python main.py
```

The interactive menu will guide you through:
- **Option 1: Process a single document** - Upload and process one PDF file
- **Option 2: Process documents from a folder (batch)** - Provide a folder path to process multiple PDFs sequentially
- **Option 3: View processing results** - Review CEASE and archived records
- **Option 4: Check audit logs** - View system events and error tracking
- **Option 5: View system statistics** - See overall processing metrics
- **Option 6: Database Management** - Export records to CSV and clear database
  - View records in table format
  - Export all records to CSV file
  - Clear all records (with backup option)
- **Option 7: Exit** - Close the application

## 📖 Usage Examples

### Processing a Single Document

```python
from graph.workflow import DocumentProcessingGraph
from datetime import datetime

# Create workflow
graph = DocumentProcessingGraph()

# Process document
final_state = graph.process_document(
    document_path="/path/to/cease_letter.pdf",
    document_name="cease_001.pdf"
)

# Check results
print(f"Classification: {final_state.classification_result.classification}")
print(f"Confidence: {final_state.classification_result.confidence:.2%}")

if final_state.classification_result.classification == "CEASE":
    print(f"Sender: {final_state.extraction_result.sender_name}")
    print(f"Claims: {final_state.extraction_result.key_claims}")
```

### Batch Processing Multiple Documents

```python
from pathlib import Path
from graph.workflow import DocumentProcessingGraph

# Create workflow
graph = DocumentProcessingGraph()

# Process all PDFs in a folder
folder_path = "/path/to/documents/folder"
pdf_files = list(Path(folder_path).glob("*.pdf"))

results = []
for pdf_path in pdf_files:
    print(f"Processing: {pdf_path.name}")
    
    final_state = graph.process_document(
        document_path=str(pdf_path),
        document_name=pdf_path.name
    )
    
    results.append({
        "document": pdf_path.name,
        "classification": final_state.classification_result.classification,
        "confidence": final_state.classification_result.confidence,
        "status": final_state.processing_status
    })

# Print summary
print(f"\nProcessed {len(results)} documents")
cease_count = sum(1 for r in results if r['classification'] == 'CEASE')
print(f"CEASE documents found: {cease_count}")
```

**Or use the interactive menu option 2 for guided batch processing!**

### Programmatic Access to Results

```python
from agents.database_agent import DatabaseAgent
from agents.archival_agent import ArchivalAgent
from agents.audit_agent import AuditAgent

# Database queries
db = DatabaseAgent()
cease_records = db.get_all_cease_records()
for record in cease_records:
    print(f"{record.document_name}: {record.classification}")

# Archive queries
archive = ArchivalAgent()
archived = archive.get_archived_documents()

# Audit logs
audit = AuditAgent()
logs = audit.get_document_audit_trail("cease_001.pdf")
for log in logs:
    print(f"{log['timestamp']}: {log['event_type']} - {log['status']}")
```

### Mock Mode Testing

```bash
# Run in mock mode without any API key
MOCK_MODE=true python main.py
```

### Database Management

The system includes comprehensive database management tools accessible from the main menu (Option 6):

**View Records in Table Format**
```
Select option 6 → Select option 1
Displays all CEASE records in a formatted table with:
- Record ID
- Document name
- Classification (CEASE, IRRELEVANT, UNCERTAIN)
- Confidence score
- Received date
```

**Export Records to CSV**
```
Select option 6 → Select option 2
Exports all CEASE records to a CSV file:
- Location: storage/cease_records_export_YYYYMMDD_HHMMSS.csv
- Includes: ID, document name, classification, confidence, dates, 
  sender info, claims, actions, and deadline
- Useful for: External analysis, reporting, archival
```

**Clear Database Records**
```
Select option 6 → Select option 3
Safely delete records with:
1. Shows count of records to be deleted
2. Offers automatic export to CSV before deletion
3. Requires confirmation (type 'DELETE' to proceed)
4. Logs all deletions in audit trail
```

## 🏗️ Project Structure

```
cease_desist_system/
│
├── main.py                 # Entry point with CLI menu
├── config/
│   └── settings.py         # Configuration management
│
├── agents/                 # 7 specialized agents
│   ├── ingestion_agent.py
│   ├── classification_agent.py
│   ├── extraction_agent.py
│   ├── database_agent.py
│   ├── archival_agent.py
│   ├── hitl_agent.py
│   └── audit_agent.py
│
├── graph/
│   └── workflow.py         # LanGraph orchestration
│
├── models/
│   ├── schemas.py          # Pydantic models
│   └── db_models.py        # SQLAlchemy ORM
│
├── services/
│   ├── pdf_service.py      # PDF processing
│   └── llm_service.py      # LLM interface
│
├── utils/
│   └── logger.py           # Logging setup
│
├── storage/
│   ├── database.db         # SQLite database
│   ├── archive.csv         # Archived documents
│   └── logs/
│       ├── system.log      # Application log
│       └── audit.log       # Audit trail
│
├── tests/
│   └── test_workflow.py    # Unit tests
│
├── requirements.txt        # Dependencies
├── README.md              # This file
└── .env                   # Environment variables
```

## 🗄️ Database Schema

### CeaseRecords Table
```
- id (INTEGER, PK)
- document_name (STRING, UNIQUE)
- received_date (DATETIME)
- extracted_details (JSON) - ExtractionResult
- classification (STRING)
- reasoning (TEXT)
- confidence (FLOAT)
- full_text (TEXT)
- created_at (DATETIME)
- updated_at (DATETIME)
```

### AuditLogs Table
```
- id (INTEGER, PK)
- document_name (STRING, INDEX)
- timestamp (DATETIME, INDEX)
- event_type (STRING, INDEX) - classification, extraction, etc.
- agent (STRING)
- details (JSON)
- status (STRING) - success, failure, pending
- error_message (TEXT)
- created_at (DATETIME)
```

### ArchiveRecords Table
```
- id (INTEGER, PK)
- document_name (STRING, UNIQUE)
- received_date (DATETIME)
- classification (STRING)
- extracted_text (TEXT)
- archive_date (DATETIME)
- csv_archived (INTEGER)
- created_at (DATETIME)
```

## 🤖 Agent Descriptions

### 1. Ingestion Agent
- **Purpose**: Extract text from PDF files
- **Methods**: pdfplumber (primary) → PyPDF2 (fallback)
- **Output**: Cleaned text, page count, file size

### 2. Classification Agent
- **Purpose**: Classify documents using LLM
- **Categories**: CEASE, UNCERTAIN, IRRELEVANT
- **Output**: ClassificationResult with confidence and reasoning

### 3. Extraction Agent
- **Purpose**: Extract structured data from CEASE documents
- **Extracts**: Sender info, date, claims, requested actions, deadline
- **Output**: ExtractionResult with all fields

### 4. Database Agent
- **Purpose**: Store CEASE records in SQLite
- **Operations**: Create, read, update, delete records
- **Ensures**: Duplicate prevention via unique timestamp suffixes on document names
- **Note**: Document names are stored with timestamps (e.g., `cease_001.pdf_20260321_143022_123456`) to allow reprocessing of the same file multiple times

### 5. Archival Agent
- **Purpose**: Archive non-CEASE documents
- **Storage**: SQLite database + CSV backup
- **Maintains**: Complete audit trail with unique timestamp suffixes on document names

### 6. HITL Agent
- **Purpose**: Human review interface for uncertain documents
- **Interface**: Interactive CLI with document preview
- **Decision**: Override/confirm classification

### 7. Audit Agent
- **Purpose**: Comprehensive event logging
- **Storage**: File logs + Database logs
- **Tracks**: Every agent action, timestamps, errors

## 🛡️ Features

### Error Handling
- ✅ Graceful PDF extraction failures
- ✅ LLM call retries with exponential backoff
- ✅ Database transaction management
- ✅ Comprehensive error logging

### Security
- ✅ Type hints throughout for IDE support
- ✅ Pydantic validation for all inputs/outputs
- ✅ SQL injection protection (SQLAlchemy ORM)
- ✅ Audit trail for compliance

### Performance
- ✅ Async/await ready (LangChain streams)
- ✅ Database indexing on frequent queries
- ✅ PDF text extraction with fallback methods
- ✅ Configurable timeouts and retries
- ✅ Unique timestamp-based document naming for batch processing (allows reprocessing same files)

### Testing
- ✅ Unit tests for all agents
- ✅ Integration tests for workflow
- ✅ Mock LLM mode for offline testing
- ✅ pytest fixtures and parametrization

## 📊 Classification Examples

### CEASE - Valid Cease & Desist
```
Subject: CEASE AND DESIST NOTICE

You are in violation of trademark rights held by ACME Corporation.
We demand that you immediately cease and desist:
1. Use of the ACME name
2. Distribution of counterfeit products
3. All related trademark infringement

Deadline: April 21, 2026
```

### UNCERTAIN - Ambiguous Document
```
Subject: Notice of Concern

We have noticed that your product has some similarities to ours.
We would appreciate it if you would review your practices
and consider whether modifications might be appropriate.
```

### IRRELEVANT - Not a Cease & Desist
```
Subject: Invoice #2026-001

Thank you for your recent order. Please find attached your invoice.
Payment is due within 30 days.
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test class
pytest tests/test_workflow.py::TestClassificationAgent -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Mock mode testing
MOCK_MODE=true pytest tests/ -v
```

## 🔄 Workflow States

```
PENDING → PROCESSING → AWAITING_HUMAN_REVIEW → COMPLETED
                   ↓
                FAILED (with error message)
```

## 📝 Audit Trail Example

```
[2026-03-21 10:30:00] [INFO] cease_desist_001.pdf - ingestion - IngestionAgent - Success
[2026-03-21 10:30:05] [INFO] cease_desist_001.pdf - classification - ClassificationAgent - Success
[2026-03-21 10:30:10] [INFO] cease_desist_001.pdf - extraction - ExtractionAgent - Success
[2026-03-21 10:30:15] [INFO] cease_desist_001.pdf - database_store - DatabaseAgent - Success
[2026-03-21 10:30:20] [INFO] cease_desist_001.pdf - workflow_complete - DocumentProcessingGraph - Success
```

## 🚀 Deployment Options

### Standalone CLI
```bash
python main.py
```

### FastAPI REST API (Optional)
```python
# Save as app.py
from fastapi import FastAPI, File, UploadFile
from graph.workflow import DocumentProcessingGraph

app = FastAPI(title="Cease & Desist Processor")

@app.post("/process")
async def process_document(file: UploadFile = File(...)):
    # Implementation
    pass
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "main.py"]
```

## ⚙️ Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | groq | LLM provider (groq, openai, mock) |
| `GROQ_API_KEY` | — | Groq API key (get from https://console.groq.com) |
| `GROQ_MODEL` | llama-3.1-8b-instant | Groq model - check https://console.groq.com/docs/models for latest available models |
| `OPENAI_API_KEY` | — | OpenAI API key (alternative provider) |
| `OPENAI_MODEL` | gpt-4-turbo-preview | OpenAI model |
| `MOCK_MODE` | false | Run without API key |
| `LLM_TEMPERATURE` | 0.3 | Model temperature (0-1) |
| `LLM_RETRY_ATTEMPTS` | 3 | Retry failed LLM calls |
| `LOG_LEVEL` | INFO | Logging level |
| `AUDIT_ENABLED` | true | Enable audit logging |
| `MAX_PDF_SIZE_MB` | 50 | Max PDF file size |

## 🔐 Security Considerations

1. **API Keys**: Store `GROQ_API_KEY` and/or `OPENAI_API_KEY` in `.env`, never commit to version control
2. **Database**: SQLite suitable for development; use PostgreSQL for production
3. **Audit Logs**: Regularly backup audit.log for compliance
4. **HITL**: Ensure human reviewers are authorized users
5. **Input Validation**: All external inputs validated with Pydantic

## 📈 Performance Metrics

- Document ingestion: ~1-2 seconds per page
- Classification: ~3-5 seconds (with LLM)
- Extraction: ~3-5 seconds (with LLM)
- Database write: ~100ms
- Archive write: ~50ms
- **Total end-to-end**: ~10-20 seconds per document

## 🐛 Troubleshooting

### LLM API Errors
```bash
# Check your configured provider API key
# For Groq (default):
echo $GROQ_API_KEY

# For OpenAI (alternative):
echo $OPENAI_API_KEY

# Test mock mode (works without any API key)
MOCK_MODE=true python main.py
```

### PDF Extraction Issues
```bash
# Check PDF is valid
file your_document.pdf

# Try with specific method (optional)
PDF_EXTRACTION_METHOD=pypdf python main.py
```

### Image-Based PDFs (Scanned Documents)

If you encounter "No text could be extracted from PDF" errors for scanned documents:

**Option 1: Enable EasyOCR (Simplest - No system installation)**
```bash
# Install pure Python OCR (easiest option, ~200MB download on first use)
pip install easyocr

# System will automatically use EasyOCR as final fallback
python main.py
```

**Option 2: Enable Tesseract OCR (More control)**
```bash
# Install OCR support
pip install pdf2image pytesseract

# Install Tesseract OCR engine
# Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki
# macOS: brew install tesseract
# Linux: sudo apt-get install tesseract-ocr

# System will use Tesseract if available (faster than EasyOCR)
python main.py
```

**Option 3: Convert to text-searchable PDF**
```bash
# Use external tools to convert scanned PDF to text-based PDF
# Then reprocess with the system
```

The system automatically tries in this order:
1. pdfplumber (fast, text-based PDFs)
2. PyPDF2 (fallback)
3. Tesseract OCR (if installed - faster)
4. EasyOCR (final fallback - no system installation needed)

### Database Errors
```bash
# Check database exists
ls -la storage/database.db

# Reinitialize database
rm storage/database.db
python main.py  # Will auto-initialize
```

## 📚 References

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Groq API Reference](https://console.groq.com/docs) - RECOMMENDED provider
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference) - Alternative provider
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 📄 License

This project is provided as-is for production use.

## 👤 Support

For issues or questions:
1. Check audit logs: `tail -f storage/logs/audit.log`
2. Review error messages in `storage/logs/system.log`
3. Enable debug logging: `LOG_LEVEL=DEBUG`

## 🎯 Future Enhancements

- [ ] FastAPI REST endpoint for cloud deployment
- [ ] Multi-language support
- [ ] Advanced NLP for claim detection
- [ ] Integration with legal databases
- [ ] Machine learning model fine-tuning
- [ ] Batch processing support
- [ ] Web dashboard for monitoring
- [ ] Email notification system

---

**Version**: 1.0.0  
**Last Updated**: March 21, 2026  
**Python Version**: 3.11+

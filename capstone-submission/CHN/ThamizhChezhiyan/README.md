# Enterprise Document Processing System (EDPS)

## Business problem
A scalable system to handle Cease & Desist document workflows automatically. Reduces manual triage and improves compliance by classifying documents and routing them to the right outcome (Cease database, Uncertain review, Irrelevant archive).

## Technical architecture
- **Frontend**: React + Vite
  - Tabs: Dashboard / Documents / Review / Audit / Settings
  - Upload interface, status tiles, notifications
- **Backend**: FastAPI (port 8000)
  - API endpoints for health/status/process/review/audit
- **Agents**: Modular pipeline in `src/agents`
  - `ManagerAgent`: Orchestrates workflow state graph
  - `ClassificationAgent`: LLM scoring + classification + extracted details
  - `DatabaseAgent`: SQLite Cease request persistence
  - `ArchivingAgent`: CSV archiving for irrelevant documents
  - `HITLAgent`: Human review queue and decision decisions
  - `AuditAgent`: Event logging
- **Persistence**:
  - `archive/irrelevant_documents.csv`
  - `logs/audit_log.json`, `logs/review_queue.json`, `logs/review_decisions.json`
  - SQLite DB (via SQLAlchemy models)

## Setup
1. `python -m venv .venv`
2. `source .venv/bin/activate` (macOS/Linux) or `.venv\Scripts\activate` (Windows)
3. `pip install -r requirements.txt`
4. `cd frontend && npm install`

## Configuration
Create `.env` with:
```
GROQ_API_KEY=your_api_key
MODEL_NAME=your_preferred_llm_model
```

## Run
### Run all (backend + frontend)
```bash
./run_web.sh
```

### Backend only
```bash
source .venv/bin/activate
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend only
```bash
cd frontend
npm run dev
```

Open `http://localhost:3008`

### CLI mode
```bash
python main.py
```

## Features
- Total/cease/irrelevant/pending dashboard metrics
- LLM classification and confidence based routing
- Human review decision path commits to DB/archive
- Audit trail persisted for compliance
- Notifications auto-dismiss (3s) or on click

## Troubleshooting
- `curl -s http://localhost:8000/health`
- `curl -s http://localhost:8000/status | python -m json.tool`
- `cat logs/audit_log.json | python -m json.tool`
- `head archive/irrelevant_documents.csv`
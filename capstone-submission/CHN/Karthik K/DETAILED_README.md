# 🛑 Cease & Desist Document Processing System

An intelligent **multi-agent AI system** that automates the classification, extraction, and routing of Cease & Desist documents — eliminating manual review for high-confidence cases while keeping humans in control for uncertain ones.

---

## 📋 Table of Contents

1. [What This System Does](#what-this-system-does)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the System](#running-the-system)
7. [Using the Web Interface](#using-the-web-interface)
8. [Observability — Arize Phoenix](#observability--arize-phoenix)
9. [Output Files](#output-files)
10. [Project Structure](#project-structure)
11. [Troubleshooting](#troubleshooting)
12. [API Reference](#api-reference)

---

## What This System Does

Enterprises receive Cease & Desist (C&D) letters that must be reviewed, classified, and acted upon. This system automates that pipeline:

```
Upload PDFs (web UI or CLI)
        │
        ▼
Memory Agent — already processed? → skip (duplicate)
        │
        ▼
Document Loader — PDF → PNG pages → Groq vision → extracted text
        │
        ▼
Classification Agent — llama-3.3-70b scores document against
        │               3 mandatory C&D criteria [A][B][C]
        │               Returns classification + honest confidence score
        │
        ├── confidence > 95% + "cease"      → Database Agent → SQLite ✅
        ├── confidence > 95% + "irrelevant" → Archiving Agent → flat file 📁
        └── confidence ≤ 95% (any class)    → HITL Agent → human reviews 👤
                                                    │
                                          Human classifies in web UI
                                          (selects class + provides reason)
                                                    │
                                      ┌─────────────┴─────────────┐
                                   cease                      irrelevant
                                      │                           │
                                 Database Agent           Archiving Agent
                                      │
                              Audit Agent ← always runs last
                                      │
                              audit_log.jsonl
```

### Key Features

| Feature | Description |
|---|---|
| **7-agent pipeline** | Each agent has exactly one responsibility |
| **LLM PDF extraction** | Groq vision model (llama-4-scout) reads PDFs as images — no OCR library |
| **Criteria-based confidence** | LLM scores against 3 mandatory C&D criteria — not abstract self-assessment |
| **Threshold routing** | `confidence > 95%` → auto-route; `≤ 95%` → human review |
| **Threshold hidden from LLM** | LLM never sees the cutoff, preventing score gaming |
| **HITL web UI** | Review modal with classification buttons + mandatory reason field |
| **Memory & dedup** | Audit log checked before processing — duplicates skipped automatically |
| **Full audit trail** | Every decision logged to JSONL with confidence, reason, reviewer |
| **Arize Phoenix tracing** | ONE unified trace per document — all agent spans nested under root |
| **Multi-language support** | LLM translates non-English documents before classification |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      React Frontend                          │
│   Drag & drop upload · Result cards · HITL review modal      │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP (port 3000 → 8001)
┌──────────────────────────────▼───────────────────────────────┐
│                  FastAPI Backend (server.py)                  │
│  POST /process · POST /hitl-decision · GET /hitl-pending     │
│  WEB_MODE=1 set here — prevents input() blocking in agents   │
└──────────────────────────────┬───────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────┐
│            LangGraph Pipeline (run_langgraph.py)             │
│                                                              │
│  memory_check → document_loader → classification_agent       │
│       │               │                    │                 │
│  (duplicate?)    (Groq vision)    confidence > 95%?          │
│                                  YES ──────┼──────── NO      │
│                               cease    irrelevant  hitl      │
│                                  │         │        │        │
│                              database  archiving  hitl_agent │
│                                  └─────────┴────────┘        │
│                                           │                  │
│                                       audit_agent            │
└──────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
       cease_desist.db  audit_log.jsonl  irrelevant_documents.txt
                               │
              ┌────────────────┘
       ~/.phoenix/ (Arize Phoenix trace store)
```

### Models Used

| Model | Provider | Purpose |
|---|---|---|
| `meta-llama/llama-4-scout-17b-16e-instruct` | Groq | PDF page image → text extraction |
| `llama-3.3-70b-versatile` | Groq | Document classification + confidence scoring |

---

## Prerequisites

| Requirement | Version | Check command |
|---|---|---|
| Python | 3.10+ | `python3 --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Groq API key | — | [console.groq.com](https://console.groq.com) |

---

## Installation

### Step 1 — Download the project

```bash
cd ~/Downloads
unzip capstone-project.zip
cd capstone-project
```

### Step 2 — Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### Step 3 — Install Python dependencies

```bash
pip install -r requirements_server.txt
```

`requirements_server.txt` includes:
```
fastapi>=0.110.0
uvicorn>=0.27.0
python-multipart>=0.0.9
langchain-core>=0.3
langchain-groq>=0.2
langgraph>=0.2
pymupdf>=1.24
python-dotenv>=1.0
```

### Step 4 — Install Arize Phoenix (optional but recommended)

```bash
pip install arize-phoenix arize-phoenix-otel opentelemetry-sdk
```

### Step 5 — Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Configuration

### Step 1 — Create your `.env` file

```bash
cp .env.example .env
```

### Step 2 — Add your API key

Open `.env` and fill in:

```env
GROQ_API_KEY=gsk_your_key_here
```

Get your Groq API key at: https://console.groq.com/keys

### Step 3 — Enable WAL mode on SQLite (one-time)

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('cease_desist.db')
conn.execute('PRAGMA journal_mode=WAL')
conn.commit()
conn.close()
print('WAL mode enabled')
"
```

> Close **DB Browser for SQLite** before running this if it's open.


```

---

## Running the System

### Option A — With web interface (recommended)

You need **two terminals open simultaneously**.

**Terminal 1 — Backend server:**
```bash
source venv/bin/activate
python server.py
```
Expected: `INFO: Uvicorn running on http://0.0.0.0:8001`

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```
Expected: `➜ Local: http://localhost:3000/`

**Terminal 3 — Arize Phoenix (optional):**
```bash
python -m phoenix.server.main
```
Expected: `🌍 Open the Phoenix UI at http://localhost:6006`

Then open **http://localhost:3000** in your browser.

---

### Option B — CLI only (no web interface)

```bash
source venv/bin/activate

# Single file
python run_langgraph.py sample_docs/cease_letter.pdf

# Entire folder
python run_langgraph.py sample_docs/
```

In CLI mode, HITL documents pause for console input.

---

## Using the Web Interface

### 1. Upload

- Drag and drop one or more PDFs, or click to browse
- Files are listed with name and size
- Click **×** to remove a file from the queue
- Duplicate documents are detected automatically

### 2. Process

- Click **"Process N Documents"**
- Each PDF page is rendered as an image and sent to Groq vision
- `llama-3.3-70b` then classifies and scores each document
- A loading indicator shows while processing

### 3. Results

Each document gets a colour-coded result card:

| Colour | Meaning | Action taken |
|---|---|---|
| 🟢 Green | Cease & Desist | Stored in SQLite database |
| 🔴 Red | Irrelevant | Archived to flat file with reason |
| 🟣 Purple | Needs Review | Awaiting human decision |

Click any card to expand and see confidence bar, sender details, classification reason, and irrelevant reason.

### 4. Human Review (HITL)

When a document has confidence ≤ 95%, a purple **"Review →"** button appears:

1. Click **"Review →"**
2. Modal opens showing LLM suggestion, confidence %, reason, and document preview
3. Select **Cease & Desist** or **Irrelevant**
4. Enter a reason (required for Irrelevant, optional for Cease)
5. Click **Confirm** — card updates immediately with your decision

### 5. Process More

Click **"← Process more"** to return to the upload screen and process another batch.

---

## Observability — Arize Phoenix

The system includes full LLM observability using **Arize Phoenix** — an open-source tracing platform that stores everything locally.

### What gets traced

Every document run creates **one unified trace** in Phoenix with all agent spans nested underneath:

```
process_document  (root span — total time for one document)
  ├── memory_check_agent        ← duplicate check
  ├── document_loader_agent     ← Groq vision extraction
  │     └── [vision LLM calls]  ← one per page (auto-instrumented)
  ├── classification_agent      ← llama-3.3-70b classification
  │     └── [text LLM call]     ← confidence + classification
  ├── database_agent / archiving_agent
  └── audit_agent
```

Each span captures:

| Agent | Traced attributes |
|---|---|
| memory_check | document.name, memory.duplicate, memory.previous_class |
| document_loader | document.name, document.extracted_chars |
| classification | classification.result, classification.confidence, classification.reason |
| database / archiving | sender.name, cease.activity / irrelevant.reason |
| hitl | hitl.mode, classification.suggested, hitl.human_decision |
| audit | classification.final, reviewed_by |

### Start Phoenix

```bash
# Terminal 3 (before starting server.py)
python -m phoenix.server.main &

# Open UI
open http://localhost:6006
```

### Storage

All traces are saved locally to `~/.phoenix/` — no cloud account needed, no data leaves your machine.

---

## Output Files

Three files are generated in the project root:

### `cease_desist.db` — SQLite database

```sql
-- View all stored cease requests
SELECT document_name, sender_name, cease_activity, confidence, created_at
FROM cease_requests
ORDER BY created_at DESC;
```

Columns: `id`, `received_date`, `document_name`, `sender_name`, `sender_address`, `cease_activity`, `confidence`, `raw_text`, `created_at`

> Open with DB Browser for SQLite in **Read Only** mode while server is running to avoid database lock errors.

### `irrelevant_documents.txt` — Flat archive

One line per irrelevant document, including the specific reason:

```
2026-03-18 | invoice_q1.pdf | confidence: 88% | reason: Vendor invoice for software services. No legal demand, no cease language.
2026-03-18 | guardianship.pdf | confidence: 91% | reason: Guardianship consultation request. No stop demand, no C&D criteria present.
```

### `audit_log.jsonl` — Compliance trail

Every processed document gets one JSON line — used for compliance reporting and duplicate detection:

```json
{"timestamp":"2026-03-18T10:23:11","document_name":"cease_trademark.pdf","classification":"cease","confidence":94,"reason":"Explicit C&D from attorney","action":"Stored in DB","reviewed_by":"system"}
{"timestamp":"2026-03-18T10:25:44","document_name":"invoice.pdf","classification":"irrelevant","confidence":88,"reason":"Vendor invoice","action":"Archived","reviewed_by":"system"}
{"timestamp":"2026-03-18T10:28:01","document_name":"ambiguous.pdf","classification":"cease","confidence":71,"reason":"C&D-like but sender unclear","action":"Stored in DB","reviewed_by":"human_operator"}
```

---

## Project Structure

```
capstone-project/
│
├── run_langgraph.py            ← Main pipeline (LangGraph + Groq)
├── server.py                   ← FastAPI backend
├── requirements_server.txt     ← Python dependencies
├── .env.example                ← Environment variable template
├── .env                        ← Your API keys (not committed to git)
├── .gitignore
│
├── agents/
│   └── classification_agent.py ← Standalone classification agent module
│
├── frontend/                   ← React web interface
│   ├── src/
│   │   ├── App.jsx             ← Main UI (upload, results, HITL modal)
│   │   └── main.jsx            ← React entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js



```



## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/process` | Upload and classify one or more PDFs |
| `POST` | `/hitl-decision` | Submit human review decision |
| `GET` | `/hitl-pending` | List documents awaiting human review |
| `GET` | `/results` | Full audit log history |
| `GET` | `/stats` | Summary counts (cease / irrelevant / uncertain / hitl_pending) |

### Confidence Threshold

Configured in `run_langgraph.py`:

```python
CONFIDENCE_THRESHOLD = 95
```

| Score | Route |
|---|---|
| `> 95%` | Auto-processed (cease → DB, irrelevant → archive) |
| `≤ 95%` | Sent to HITL for human review |
| `None` (LLM omitted) | Sent to HITL (safest fallback) |

The threshold is intentionally **not shown to the LLM** in the prompt. If the LLM sees the cutoff, it games the score by returning values just above it. The LLM scores honestly based on document criteria; Python applies the routing rule.

---

## Built With

| Component | Technology |
|---|---|
| Agent orchestration | LangGraph |
| LLM provider | Groq |
| Text classification | llama-3.3-70b-versatile |
| PDF extraction | llama-4-scout-17b-16e-instruct (vision) |
| PDF rendering | PyMuPDF (fitz) |
| Backend API | FastAPI + Uvicorn |
| Database | SQLite (WAL mode) |
| Frontend | React 18 + Vite |
| Observability | Arize Phoenix + OpenTelemetry |

---

*Capstone Project · Agentic AI Training *

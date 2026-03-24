# Multi-Agent Document Classification System

## Overview
An automated pipeline that classifies legal PDF documents (specifically Cease & Desist notices) using a multi-agent architecture built with LangGraph, LangChain, and Groq LLMs.

## Architecture

```
Manager Agent → Classification Agent → Manager Agent → Database Agent → Audit Agent
                                              ↓
                                         HITL Agent (if Uncertain)
```

## Agents

| Agent | Role |
|---|---|
| **Manager Agent** | Orchestrates the workflow by routing to the correct agent based on current state |
| **Classification Agent** | Extracts text from PDF and classifies it as `Cease`, `Irrelevant`, or `Uncertain` |
| **HITL Agent** | Prompts a human to manually classify documents the AI marked as `Uncertain` |
| **Database Agent** | Inserts or updates the classification result in SQLite via the `execute_sql` tool |
| **Audit Agent** | Flushes all workflow audit log entries to a persistent text file |

## Routing Rules (Manager Agent)
1. `workflow_step = audit_log` → **end**
2. `workflow_step = database_store or archived` → **audit_agent**
3. `classification` is missing → **classification_agent**
4. `classification = Cease or Irrelevant` → **database_agent**
5. `classification = Uncertain` → **hitl_agent**

## Tools
- **`extract_pdf_text`** — Reads regular and scanned PDFs (OCR via Tesseract)
- **`execute_sql`** — Executes SQLite queries against the `document_details` table

## Database Schema
```sql
CREATE TABLE document_details (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name         TEXT,
    date_received     TEXT,
    classification    TEXT,
    confidence_score  TEXT,
    human_decision    TEXT,
    reason            TEXT,
    extraction_details TEXT,
    created_at        TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Tech Stack
- **LangGraph** — Stateful multi-agent graph orchestration
- **LangChain** — Agent creation and tool binding
- **Groq (Qwen 32B)** — Classification and manager LLM
- **Groq (GPT-OSS 120B)** — Database agent LLM
- **SQLite** — Document storage
- **LangSmith** — Workflow tracing

## How to Run
1. Upload PDF files to `/content/inputdocs/`
2. Set `GROQ_API_KEY` and `LANGSMITH_API_KEY` in Colab secrets
3. Run all cells in order
4. For `Uncertain` documents, enter `Cease` or `Irrelevant` when prompted

# Evaluation Run — 2026-03-23

**Locations processed**: CHN, HYD, BLR
**New members evaluated**: 4 (Prem, Steffina, Bhargav, Hema)
**Skipped (already evaluated)**: 0
**BLR**: No submissions found — skipped

---

## Summary — New Members This Run

| Rank (in location) | Member | Location | Technical | Design | Completion | Docs | Total | Grade |
|--------------------|--------|----------|-----------|--------|------------|------|-------|-------|
| 1 | Bhargav | HYD | 100/100 | 10/10 | 10/10 | 10/10 | 130/130 | A |
| 1 | Prem | CHN | 100/100 | 10/10 | 10/10 | 8/10 | 128/130 | A |
| 2 | Hema | HYD | 84/100 | 7/10 | 7/10 | 5/10 | 103/130 | B |
| 2 | Steffina | CHN | 80/100 | 7/10 | 7/10 | 4/10 | 98/130 | B |

---

## Individual Evaluations

---

### Prem — CHN | Total: 128/130 | Grade: A

**Submission**: `capstone-submission/CHN/Prem/Cease_Desease_Capstone_Final.ipynb`
**Framework**: LangChain/LangGraph + Groq (llama-3.1-8b-instant + llama-4-scout vision)

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | 6 distinct agents: document_loader, classifier, database, archiving, human_review, audit. Full LangGraph StateGraph with conditional routing. |
| Document Classification | 20 | 20 | Detailed SYSTEM_PROMPT with all 3 categories (cease/uncertain/irrelevant), confidence scoring, chunk-based classification with merge-priority logic. |
| Human-in-the-Loop (HITL) | 20 | 20 | Uses `interrupt()` from `langgraph.types`. Proper pause with payload (case_id, doc_name, message). Resume via `Command`. Routes to DB or archive based on human decision. Extracts data on approval. |
| Database / Persistence | 15 | 15 | SQLite `cease_cases.db` with full schema: case_id, doc_name, received_at, sender, classification, confidence_score, reasoning, final_action, is_human_involved. All required fields present. |
| Archiving | 10 | 10 | `archive_tool` writes to `irrelevant_archive.txt` with DATE, CASE, FILE, confidence score, and truncated REASON. All required fields. |
| Audit Trail | 10 | 10 | `audit_log.db` with 19-column schema: step_number, agent_name, step_status, classification, confidence, tokens_input/output, time_taken, error_message, logged_at. Per-step logging from every agent. |
| **Technical Total** | **100** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 10 | 10 | 20-field `DocumentState` TypedDict, step counter, memory_store, `generate_case_id()` with counter+timestamp, vision LLM fallback for scanned PDFs, chunk splitter. Exceptional design thinking. |
| Code Completion | 10 | 10 | All 6 agents fully implemented. Graph built and compiled with MemorySaver. Full processing loop with state per document. End-to-end runnable. |
| Documentation | 8 | 10 | Each cell has a descriptive header comment. Docstrings on `classify_chunk`, `merge_results`, `create_state`, `save_to_memory`. No dedicated markdown cells explaining architecture. Slight deduction. |
| **Metrics Total** | **28** | **30** | |

**Grand Total: 128 / 130**

**Strengths**:
- Only member to use proper LangGraph `interrupt()` + `Command(resume)` HITL pattern
- Vision LLM fallback for scanned PDFs is a thoughtful extra
- Chunk-based classification with merge-priority logic handles long documents correctly
- Dual SQLite databases (cease_cases + audit_log) with separate concerns
- Token tracking across all agents

**Areas for Improvement**:
- Add markdown cells explaining the overall architecture flow
- Increase docstring coverage on agent functions (currently only helper functions have them)

**Code Quality Notes**:
- API key loaded from Colab Secrets — good security practice
- step_counter and time_taken in every audit entry — excellent observability

---

### Steffina — CHN | Total: 98/130 | Grade: B

**Submission**: `capstone-submission/CHN/Steffina/cease_processing_steffina_k095637.ipynb`
**Framework**: LangChain/LangGraph + Groq (llama-3.3-70b-versatile)

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 22 | 25 | 5 agents in LangGraph StateGraph: loader, classify, cease, archive, hitl. Graph compiled and executed. Slightly simpler than required — no dedicated audit agent as a separate node. |
| Document Classification | 18 | 20 | 3 categories with LLM-based classification. JSON output with classification, confidence, reason. Normalization function to standardise labels. Good but prompt less detailed than expected for edge cases. |
| Human-in-the-Loop (HITL) | 15 | 20 | `hitl_agent` uses `input()` and routes via conditional edges. HITL is integrated into the graph correctly. Does not use LangGraph `interrupt()` so cannot pause/resume between sessions. |
| Database / Persistence | 11 | 15 | SQLite with documents, cease_requests, audit_logs tables. `insert_cease` stores doc_name + full text but lacks structured extracted fields (sender, violation type, deadline). |
| Archiving | 6 | 10 | `archive_document()` writes to `archive.txt`. Only stores the document filename — missing date received. |
| Audit Trail | 8 | 10 | `insert_audit` logs doc_name, classification, action_taken, timestamp, reason, confidence. Missing step tracking and token/time information. |
| **Technical Total** | **80** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 7 | 10 | `State` TypedDict defined, 5 agents with clear role names, router function with 3 branches. Reasonable structure. Early `process_document` function is a legacy artefact that should have been removed. |
| Code Completion | 7 | 10 | Graph-based implementation is complete and runnable. Early function `process_document` has a bug (expects 2 return values from `classify_document` which returns 3). The graph approach works correctly. |
| Documentation | 4 | 10 | Minimal documentation. No docstrings on agent functions. Some emoji print statements serve as progress indicators. No markdown cells or comments explaining design decisions. |
| **Metrics Total** | **18** | **30** | |

**Grand Total: 98 / 130**

**Strengths**:
- Clean LangGraph StateGraph with all 5 agent nodes
- 3-category classification with label normalisation is robust
- Graph visualisation cell included

**Areas for Improvement**:
- Add date to archive entries (required field)
- Store structured extracted fields (sender, violation, deadline) in DB, not just full text
- Replace `input()` with LangGraph `interrupt()`/`Command(resume)` for proper HITL
- Add docstrings to all agent functions
- Remove or fix the legacy `process_document` function

**Code Quality Notes**:
- **SECURITY ISSUE**: Hardcoded Groq API key found in cell 19: `client = Groq(api_key="gsk_2IBn...")`. Rotate this key immediately and use Colab Secrets or environment variables.

---

### Bhargav — HYD | Total: 130/130 | Grade: A

**Submission**: `capstone-submission/HYD/Bhargav/cease_desist_capstone_Final.ipynb`
**Framework**: LangChain/LangGraph + Groq (qwen3-32b) + ChromaDB + HuggingFace Embeddings

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | 9 nodes: read_document, retrieve_context (RAG), classify_document, router_node, action_agent, action_tool (ToolNode), after_tool, hitl_node, audit_log. Fully orchestrated StateGraph with MemorySaver. |
| Document Classification | 20 | 20 | Detailed CLASSIFIER_SYSTEM prompt with confidence threshold (0.75). JSON extraction of sender, account, email, key phrases. 3-category routing with explanations. |
| Human-in-the-Loop (HITL) | 20 | 20 | Full `interrupt()` + `Command(resume)` pattern. Rich panel for human review. `hitl_pending` list management. Decision routed back correctly. |
| Database / Persistence | 15 | 15 | `@tool store_cease_record` writes to SQLite with: received_date, processed_date, document_name, sender_name, account_number, sender_email, confidence, explanation, full_text, extracted_json. |
| Archiving | 10 | 10 | `@tool archive_irrelevant_document` appends to CSV with: archived_at, document_name, received_date, confidence, explanation. All required fields plus extras. |
| Audit Trail | 10 | 10 | `audit_log.csv` + `hitl_queue.csv` + `categorisation_summary.csv`. Multiple audit outputs. Classification result, action, confidence, HITL flag per document. |
| **Technical Total** | **100** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 10 | 10 | CONFIG dict with all paths and parameters, CEASE/UNCERTAIN/IRRELEVANT constants, conversational RAG chain (Lab2_2 pattern), clean TypedDict with typed fields, ASCII architecture diagram rendered in cell. |
| Code Completion | 10 | 10 | All 9 nodes implemented. GitHub PDF downloader with fallback. ChromaDB vector store. Results dashboard with Rich tables. Query cells for DB/archive/audit/HITL. Fully end-to-end runnable. |
| Documentation | 10 | 10 | Markdown cell for every section, docstrings on every node (`"""Node N: ..."""`), inline comments on all non-trivial logic, architecture diagram with mermaid + ASCII fallback. Exceptional. |
| **Metrics Total** | **30** | **30** | |

**Grand Total: 130 / 130**

**Strengths**:
- Only member to incorporate a conversational RAG layer (ChromaDB + HuggingFace embeddings) for context retrieval
- GitHub PDF downloader with local fallback shows production-readiness thinking
- CONFIG dict makes the system parameterised and portable
- Rich results dashboard provides excellent observability
- Perfect documentation coverage — every node, every tool, every section explained

**Areas for Improvement**:
- None significant. Outstanding submission.

**Code Quality Notes**:
- API key loaded from Colab Secrets — good security practice
- `reasoning_format="parsed"` for Qwen3 shows deep framework knowledge
- Error handling present throughout (try/except on every node)

---

### Hema — HYD | Total: 103/130 | Grade: B

**Submission**: `capstone-submission/HYD/Hema/Capstone_Hema.ipynb`
**Framework**: LangChain/LangGraph + OpenAI SDK (via Groq endpoint) + pytesseract OCR

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 22 | 25 | 7 nodes: ocr, agent, tools (ToolNode), human_review, human_to_db, human_to_csv, audit. Good structure but `human_to_db_node` body appears incomplete in submission. |
| Document Classification | 14 | 20 | 3 categories handled via routing, but classification relies on keyword matching (cease/desist → valid, behalf → uncertain, else → irrelevant) rather than full LLM semantic analysis. |
| Human-in-the-Loop (HITL) | 17 | 20 | `human_review_node` uses `input()`. Conditional routing via `human_router` to `human_to_db` or `human_to_csv`. Well integrated but uses `input()` not LangGraph `interrupt()`. |
| Database / Persistence | 13 | 15 | SQLite with documents + audit_logs. `@tool save_to_db_tool` stores file_name, doc_name, doc_date, extracted_details. Missing one required field (no explicit sender/violation extraction). |
| Archiving | 10 | 10 | `@tool save_to_csv_tool` writes file_name, document_name, document_date to CSV. All required fields. |
| Audit Trail | 8 | 10 | `save_audit_log` captures file_name, classification, action, human_decision, timestamp. Missing confidence score and reasoning in audit entries. |
| **Technical Total** | **84** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 7 | 10 | CONFIG constants (DB_FILE, CSV_FILE), OCR-first pipeline makes sense for scanned PDFs, `validate_decision` function shows thoughtful self-checking. `detect_keyword` logic is simple but clear. |
| Code Completion | 7 | 10 | Most nodes implemented. `human_to_db_node` body missing from visible code (appears truncated). Core pipeline works. `validate_decision` defined but output not used in routing. |
| Documentation | 5 | 10 | Section dividers (`# ----`) and node labels in comments. No docstrings on any function. Print statements with emoji act as informal logs. No markdown cells. |
| **Metrics Total** | **19** | **30** | |

**Grand Total: 103 / 130**

**Strengths**:
- pytesseract + pdf2image OCR is a practical choice for scanned PDFs
- `validate_decision` function shows good thinking about correctness checking
- 7-node graph with clear routing between human decision paths
- @tool decorator used correctly for DB and CSV actions

**Areas for Improvement**:
- Replace keyword matching with LLM-based semantic classification for better accuracy
- Complete `human_to_db_node` implementation (body missing)
- Replace `input()` with LangGraph `interrupt()`/`Command(resume)`
- Add confidence score and reasoning to audit log entries
- Add docstrings to all node functions

**Code Quality Notes**:
- API key loaded from Colab Secrets — good security practice
- `validate_decision` is defined but its output is not used in routing — connect this to improve correctness

---

## Updated Location Rankings

### CHN — Full Leaderboard

| Rank | Member | Technical | Design | Completion | Docs | Total | Grade | Framework |
|------|--------|-----------|--------|------------|------|-------|-------|-----------|
| 1 | Prem | 100 | 10 | 10 | 8 | 128 | A | LangChain/LangGraph |
| 2 | Steffina | 80 | 7 | 7 | 4 | 98 | B | LangChain/LangGraph |

### HYD — Full Leaderboard

| Rank | Member | Technical | Design | Completion | Docs | Total | Grade | Framework |
|------|--------|-----------|--------|------------|------|-------|-------|-----------|
| 1 | Bhargav | 100 | 10 | 10 | 10 | 130 | A | LangChain/LangGraph |
| 2 | Hema | 84 | 7 | 7 | 5 | 103 | B | LangChain/LangGraph |

### BLR

No submissions received.

---

## Overall Statistics

- **Total members evaluated**: 4
- **Overall average score**: 114.75 / 130 (88.3%)
- **Grade distribution**: A: 2 | B: 2 | C: 0 | D: 0 | F: 0
- **Perfect score**: Bhargav (130/130)
- **Most common gap**: Documentation (avg 6.75/10) and Archiving (missing date field)
- **Framework**: All 4 members used LangChain/LangGraph
- **Security issues**: 1 hardcoded API key (Steffina — rotate immediately)

---

## Recommendations

1. **HITL pattern**: 3 of 4 members used `input()` instead of LangGraph `interrupt()`/`Command(resume)`. Run a 30-min follow-up session on proper interrupt/resume with MemorySaver.
2. **Documentation**: Average documentation score was 6.75/10. Encourage learners to add markdown cells and docstrings — the difference between Bhargav (10/10) and Steffina (4/10) is significant for maintainability.
3. **Archiving completeness**: Steffina's archive missed the required `received_date` field. Revisit the archiving requirements in next session.
4. **Security awareness**: Steffina hardcoded a Groq API key — use this as a teaching moment for the group on secrets management.
5. **Bhargav** is an excellent peer mentor candidate — their RAG integration and documentation quality are outstanding examples for the group.

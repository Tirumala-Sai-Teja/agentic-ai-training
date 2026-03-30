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
- **SECURITY ISSUE**: Hardcoded Groq API key found in cell 19: `client = Groq(api_key="<yourpassword>")`. Rotate this key immediately and use Colab Secrets or environment variables.

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

---

# Evaluation Run — 2026-03-29

**Locations processed**: CHN, HYD, BLR
**New members evaluated**: 52 (21 CHN + 13 HYD + 18 BLR)
**Skipped (already evaluated)**: 2 (Prem — CHN, Steffina — CHN)
**No submission**: " Rajendra Raju" (CHN) — folder not found
**HYD note**: Previously evaluated "Bhargav" and "Hema" retained in rankings; new cohort includes "Bhargav Mangavalli" and "Hema Katyal" as distinct members.

---

## Summary — New Members This Run

| Rank (in location) | Member | Location | Technical | Design | Completion | Docs | Total | Grade |
|--------------------|--------|----------|-----------|--------|------------|------|-------|-------|
| 1 | Karthik K | CHN | 100/100 | 10/10 | 10/10 | 10/10 | 130/130 | A |
| 3 | Ansari | CHN | 100/100 | 9/10 | 10/10 | 9/10 | 128/130 | A |
| 4 | Marimuthu | CHN | 98/100 | 9/10 | 9/10 | 8/10 | 124/130 | A |
| 5 | ThamizhChezhiyan | CHN | 96/100 | 9/10 | 9/10 | 9/10 | 123/130 | A |
| 6 | Kartik R | CHN | 95/100 | 9/10 | 9/10 | 8/10 | 121/130 | A |
| 7 | Sudhakar | CHN | 93/100 | 8/10 | 9/10 | 8/10 | 118/130 | A |
| 8 | Bharath | CHN | 91/100 | 8/10 | 9/10 | 7/10 | 115/130 | B |
| 9 | Thiru | CHN | 90/100 | 8/10 | 9/10 | 7/10 | 114/130 | B |
| 10 | Prasanna | CHN | 84/100 | 7/10 | 8/10 | 8/10 | 107/130 | B |
| 11 | Sathya | CHN | 83/100 | 8/10 | 8/10 | 7/10 | 106/130 | B |
| 12 | Siva | CHN | 82/100 | 8/10 | 9/10 | 7/10 | 106/130 | B |
| 13 | Praveen | CHN | 82/100 | 8/10 | 7/10 | 7/10 | 104/130 | B |
| 14 | Boopathi | CHN | 80/100 | 7/10 | 8/10 | 5/10 | 100/130 | B |
| 15 | Mani | CHN | 78/100 | 8/10 | 8/10 | 6/10 | 100/130 | B |
| 17 | Magdaleen | CHN | 77/100 | 7/10 | 7/10 | 7/10 | 98/130 | B |
| 18 | Divya | CHN | 74/100 | 7/10 | 7/10 | 7/10 | 95/130 | C |
| 19 | Ramanakumar | CHN | 72/100 | 7/10 | 8/10 | 7/10 | 94/130 | C |
| 20 | Ramkumar | CHN | 73/100 | 6/10 | 6/10 | 6/10 | 91/130 | C |
| 21 | Jayaram | CHN | 59/100 | 6/10 | 7/10 | 6/10 | 78/130 | C |
| 22 | Mragya | CHN | 60/100 | 5/10 | 6/10 | 4/10 | 75/130 | C |
| 23 | Saravana | CHN | 51/100 | 6/10 | 6/10 | 6/10 | 69/130 | D |
| 2 | Bhargav Mangavalli | HYD | 100/100 | 10/10 | 10/10 | 9/10 | 129/130 | A |
| 3 | Surya Ch | HYD | 100/100 | 9/10 | 9/10 | 8/10 | 126/130 | A |
| 4 | Sasikala Annam | HYD | 93/100 | 9/10 | 9/10 | 9/10 | 120/130 | A |
| 5 | Sudileti Rajesh | HYD | 93/100 | 9/10 | 9/10 | 8/10 | 119/130 | A |
| 6 | Keerthi Chiluvuri | HYD | 90/100 | 8/10 | 8/10 | 7/10 | 113/130 | B |
| 7 | Suresh Reddy | HYD | 90/100 | 8/10 | 8/10 | 7/10 | 113/130 | B |
| 8 | Geetamadhuri Mallidi | HYD | 88/100 | 8/10 | 8/10 | 8/10 | 112/130 | B |
| 10 | Ravi Kvs | HYD | 84/100 | 7/10 | 6/10 | 5/10 | 102/130 | B |
| 11 | Hema Katyal | HYD | 74/100 | 6/10 | 7/10 | 5/10 | 92/130 | C |
| 12 | Praveen Kumar | HYD | 74/100 | 6/10 | 7/10 | 5/10 | 92/130 | C |
| 13 | Sushma Reddy | HYD | 74/100 | 6/10 | 7/10 | 5/10 | 92/130 | C |
| 14 | Utkarsh Rajpal | HYD | 64/100 | 7/10 | 7/10 | 5/10 | 83/130 | C |
| 15 | Bala Nagendra | HYD | 59/100 | 7/10 | 5/10 | 6/10 | 77/130 | D |
| 1 | KarthikeyanRamamoorthy | BLR | 100/100 | 9/10 | 10/10 | 9/10 | 128/130 | A |
| 2 | AdityaSinha | BLR | 100/100 | 9/10 | 9/10 | 9/10 | 127/130 | A |
| 3 | Jayajeet | BLR | 100/100 | 9/10 | 9/10 | 9/10 | 127/130 | A |
| 4 | Parminder | BLR | 100/100 | 9/10 | 9/10 | 9/10 | 127/130 | A |
| 5 | Mahesh | BLR | 98/100 | 9/10 | 9/10 | 8/10 | 124/130 | A |
| 6 | RishavBhardwaj | BLR | 98/100 | 9/10 | 9/10 | 8/10 | 124/130 | A |
| 7 | Amruth | BLR | 86/100 | 8/10 | 8/10 | 7/10 | 109/130 | B |
| 8 | SachinBontadka | BLR | 86/100 | 8/10 | 8/10 | 7/10 | 109/130 | B |
| 9 | Pooja | BLR | 81/100 | 8/10 | 8/10 | 8/10 | 105/130 | B |
| 10 | VishalKumar | BLR | 81/100 | 7/10 | 8/10 | 7/10 | 103/130 | B |
| 11 | Archana | BLR | 82/100 | 7/10 | 7/10 | 5/10 | 101/130 | B |
| 12 | AbhishekAggarwal | BLR | 74/100 | 7/10 | 7/10 | 6/10 | 94/130 | C |
| 13 | Nagarjuna | BLR | 71/100 | 6/10 | 7/10 | 5/10 | 89/130 | C |
| 14 | SnehaSk | BLR | 70/100 | 6/10 | 7/10 | 6/10 | 89/130 | C |
| 15 | OmJha | BLR | 69/100 | 6/10 | 7/10 | 5/10 | 87/130 | C |
| 16 | SudarsanRao | BLR | 69/100 | 6/10 | 6/10 | 5/10 | 86/130 | C |
| 17 | Sweta | BLR | 43/100 | 4/10 | 5/10 | 4/10 | 56/130 | F |
| 18 | Rajkumar | BLR | 12/100 | 3/10 | 3/10 | 3/10 | 21/130 | F |

---

## Individual Evaluations — CHN

---

### Karthik K — CHN | Total: 130/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Enterprise-grade LangGraph with Arize Phoenix tracing; all 6 agent nodes cleanly separated |
| Document Classification | 20 | 20 | All 3 categories with confidence-based routing, detailed classification prompts |
| Human-in-the-Loop (HITL) | 20 | 20 | Full LangGraph interrupt() with pause/resume; uncertain cases correctly routed |
| Database / Persistence | 15 | 15 | SQLite with all required fields: date_received, document_name, extracted_details |
| Archiving | 10 | 10 | Flat-file archive with date and document name for irrelevant documents |
| Audit Trail | 10 | 10 | Complete audit log with timestamp, classification, action, explanation |
| **Technical Total** | **100** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 10 | 10 | Perfect agent separation, consistent naming, well-defined flow with Arize observability |
| Code Completion | 10 | 10 | All components fully implemented and runnable end-to-end |
| Documentation | 10 | 10 | Docstrings on all agents, markdown cells, demo video, README — exceptional |
| **Metrics Total** | **30** | **30** | |

**Grand Total: 130 / 130**

**Strengths**:
- Perfect implementation with Arize Phoenix tracing integration
- Confidence-based HITL routing is well-designed
- Demo video and comprehensive documentation set the bar for the cohort

**Areas for Improvement**:
- No significant gaps — could add async batch processing for production scale

---

### Ansari — CHN | Total: 128/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Full 7-agent LangGraph with clean file separation; all rubric roles covered |
| Document Classification | 20 | 20 | All 3 categories with LLM-based routing |
| Human-in-the-Loop (HITL) | 20 | 20 | Complete HITL loop with CLI interface routing decisions back into workflow |
| Database / Persistence | 15 | 15 | SQLAlchemy ORM with all required fields |
| Archiving | 10 | 10 | Dedicated archiving agent writing flat file with date and document name |
| Audit Trail | 10 | 10 | Complete audit trail with all required fields |
| **Technical Total** | **100** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 9 | 10 | Exceptional modular file structure; minor duplicate logic in database_node |
| Code Completion | 10 | 10 | All 7 agents fully implemented; end-to-end runnable |
| Documentation | 9 | 10 | Comprehensive docstrings and README; could add architecture overview |
| **Metrics Total** | **28** | **30** | |

**Grand Total: 128 / 130**

**Strengths**:
- Full 7-agent modular project with clean file separation and SQLAlchemy ORM
- Complete HITL loop routing decisions back into workflow

**Areas for Improvement**:
- Reduce duplicate logic in database_node for CEASE and human-CEASE paths
- Add a dedicated extraction agent for uncertain docs

---

### Marimuthu — CHN | Total: 124/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Comprehensive LangGraph notebook with all 6 agent roles |
| Document Classification | 20 | 20 | All 3 categories with LLM-based routing |
| Human-in-the-Loop (HITL) | 18 | 20 | Dual HITL interfaces (Streamlit + console); not fully blocking in graph |
| Database / Persistence | 15 | 15 | SQLite with all required fields |
| Archiving | 10 | 10 | Dedicated archive node with flat file |
| Audit Trail | 10 | 10 | Comprehensive audit with all fields |
| **Technical Total** | **98** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 9 | 10 | Strong design with vision extraction for scanned PDFs |
| Code Completion | 9 | 10 | Near-complete; dual HITL adds complexity |
| Documentation | 8 | 10 | Good inline comments; could add more architecture markdown |
| **Metrics Total** | **26** | **30** | |

**Grand Total: 124 / 130**

**Strengths**:
- Dual HITL interfaces (Streamlit UI + console) show production thinking
- Vision extraction for scanned PDFs is a thoughtful extra

**Areas for Improvement**:
- Simplify HITL implementation to avoid dual-path complexity

---

### ThamizhChezhiyan — CHN | Total: 123/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Enterprise-grade multi-file system with SQLAlchemy ORM and FastAPI backend |
| Document Classification | 20 | 20 | All 3 categories with comprehensive routing |
| Human-in-the-Loop (HITL) | 18 | 20 | Full HITL queue system; slightly non-blocking within LangGraph workflow |
| Database / Persistence | 14 | 15 | SQLAlchemy ORM with all fields; minor gap in one required field |
| Archiving | 10 | 10 | Flat-file archiving with date and document name |
| Audit Trail | 9 | 10 | Comprehensive audit entries; explanation field could be richer |
| **Technical Total** | **96** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 9 | 10 | Professional architecture with retry logic |
| Code Completion | 9 | 10 | All major components complete |
| Documentation | 9 | 10 | Comprehensive docstrings on all agents |
| **Metrics Total** | **27** | **30** | |

**Grand Total: 123 / 130**

**Strengths**:
- Enterprise-grade architecture with SQLAlchemy ORM and FastAPI backend
- Retry logic and comprehensive docstrings demonstrate production intent

**Areas for Improvement**:
- Make HITL blocking within the LangGraph workflow
- Add explanation field to each audit entry

---

### Kartik R — CHN | Total: 121/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Comprehensive 7-agent LangGraph notebook |
| Document Classification | 20 | 20 | All 3 categories with confidence-based routing |
| Human-in-the-Loop (HITL) | 18 | 20 | Confidence threshold routing; HITL integrated but could fully leverage interrupt() |
| Database / Persistence | 14 | 15 | SQLite with all required fields; one minor gap |
| Archiving | 9 | 10 | Flat-file archive present; minor format issue |
| Audit Trail | 9 | 10 | Complete audit in SQLite; good coverage |
| **Technical Total** | **95** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 9 | 10 | Well-structured confidence-based routing design |
| Code Completion | 9 | 10 | All components working end-to-end |
| Documentation | 8 | 10 | Good coverage; could add more inline comments |
| **Metrics Total** | **26** | **30** | |

**Grand Total: 121 / 130**

**Strengths**:
- Comprehensive 7-agent system with confidence threshold routing
- Complete audit trail in SQLite

**Areas for Improvement**:
- Ensure interrupt-based HITL fully pauses workflow for true session persistence

---

### Sudhakar — CHN | Total: 118/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 22 | 25 | Complete LangGraph notebook with 6 nodes |
| Document Classification | 20 | 20 | All 3 categories with LLM routing |
| Human-in-the-Loop (HITL) | 19 | 20 | Uses LangGraph interrupt() correctly; LangSmith tracing |
| Database / Persistence | 14 | 15 | Good SQLite schema; minor gap |
| Archiving | 9 | 10 | Flat file archive present; missing date on some entries |
| Audit Trail | 9 | 10 | Full audit to file; good coverage |
| **Technical Total** | **93** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 8 | 10 | Clean design with LangSmith tracing integration |
| Code Completion | 9 | 10 | Near-complete; minor archive date gap |
| Documentation | 8 | 10 | Good comments; could add more markdown cells |
| **Metrics Total** | **25** | **30** | |

**Grand Total: 118 / 130**

**Strengths**:
- Proper LangGraph interrupt() usage with LangSmith tracing
- Complete 6-node graph with all paths

**Areas for Improvement**:
- Add document_name and received date to all archive flat file entries

---

### Bharath — CHN | Total: 115/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Excellent single-file LangGraph with Command-based routing and full audit JSON; complete HITL with proper routing to sqlAgent or fileArchiving.
**Areas for Improvement**: Modularize into separate files; add date_received as a dedicated DB column separate from created_at.

**Technical Total: 91/100 | Quality: 24/30**

---

### Thiru — CHN | Total: 114/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: 7-node LangGraph notebook with complete routing including uncertain→HITL→cease_db/archive path; audit_agent called throughout.
**Areas for Improvement**: Add date_received field to database schema; modularize into separate Python files.

**Technical Total: 90/100 | Quality: 24/30**

---

### Prasanna — CHN | Total: 107/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Well-organized notebook with batch processing and dual DB tables; clear markdown documentation throughout.
**Areas for Improvement**: Replace DB storage for irrelevant docs with flat-file archive per spec; add a proper audit trail file.

**Technical Total: 84/100 | Quality: 23/30**

---

### Sathya — CHN | Total: 106/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Well-structured class-based agents with all 6 roles and working HITL; all 3 categories in outputs.
**Areas for Improvement**: Remove Chinook.db tutorial remnant; strengthen audit trail with explanation and action taken fields.

**Technical Total: 83/100 | Quality: 23/30**

---

### Siva — CHN | Total: 106/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Production-quality LangGraph with interrupt_before HITL mechanism and Streamlit UI; clean modular file structure.
**Areas for Improvement**: Replace Python logging with structured audit trail file/DB; add explicit date_received field to DB schema.

**Technical Total: 82/100 | Quality: 24/30**

---

### Praveen — CHN | Total: 104/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Manager agent orchestration pattern; well-documented prompts and structured classification output.
**Areas for Improvement**: Add a dedicated archive agent for irrelevant documents; complete the HITL routing back to archive path.

**Technical Total: 82/100 | Quality: 22/30**

---

### Boopathi — CHN | Total: 100/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Clean multi-file architecture with all 4 core agents as separate modules; functional end-to-end pipeline.
**Areas for Improvement**: Improve audit trail to include timestamp and explanation; add docstrings and README.

**Technical Total: 80/100 | Quality: 20/30**

---

### Mani — CHN | Total: 100/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Good modular structure with 8+ nodes and memory-based learning; validates docs before routing to HITL.
**Areas for Improvement**: Add date_received to database schema; strengthen archive with more document metadata fields.

**Technical Total: 78/100 | Quality: 22/30**

---

### Magdaleen — CHN | Total: 98/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Well-structured 5-node LangGraph with 3-way classification and HITL; route_archive logic handles post-DB archive routing.
**Areas for Improvement**: Add a dedicated flat-file archive for irrelevant docs; strengthen HITL to handle all uncertain-to-irrelevant routing properly.

**Technical Total: 77/100 | Quality: 21/30**

---

### Divya — CHN | Total: 95/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Good LangGraph notebook with Arize Phoenix tracing and SQLite checkpointing; all 3 classification paths present.
**Areas for Improvement**: Replace keyword-matching classification with full LLM routing; add date to archive.txt writes.

**Technical Total: 74/100 | Quality: 21/30**

---

### Ramanakumar — CHN | Total: 94/130 | Grade: C

**Framework**: Other (class-based, no LangGraph)

**Strengths**: Complete OOP pipeline with MainController and 5 well-defined classes; DB stores comprehensive document information.
**Areas for Improvement**: Adopt LangGraph for proper graph orchestration; add proper blocking HITL instead of queue-only approach.

**Technical Total: 72/100 | Quality: 22/30**

---

### Ramkumar — CHN | Total: 91/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Good educational progression from keyword to LLM classification; LangGraph nodes and routing present.
**Areas for Improvement**: Replace in-memory database list with SQLite persistence; remove tutorial scaffolding cells from final submission.

**Technical Total: 73/100 | Quality: 18/30**

---

### Jayaram — CHN | Total: 78/130 | Grade: C

**Framework**: Other (BART zero-shot, no LangGraph)

**Strengths**: Creative multimodal classification using BART zero-shot with image OCR fallback; conversation context memory via DBTools.
**Areas for Improvement**: Adopt LangGraph or graph framework for orchestration; persist audit log to file or database.

**Technical Total: 59/100 | Quality: 19/30**

---

### Mragya — CHN | Total: 75/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Clean LangGraph pipeline with functional 3-way classification and HITL via input(); compact readable code.
**Areas for Improvement**: Remove hardcoded API key (security risk — rotate immediately); add proper archiving flat file; add timestamps to audit log.

**Security Note**: Hardcoded API key detected (`GROQ_API_KEY` set directly in code). Value redacted as `<yourpassword>`. Please rotate immediately.

**Technical Total: 60/100 | Quality: 15/30**

---

### Saravana — CHN | Total: 69/130 | Grade: D

**Framework**: Google ADK

**Strengths**: Creative Google ADK single-agent approach with LiteLLM bridge; HITL naturally integrated through agent interaction.
**Areas for Improvement**: Implement 3-way classification (Cease/Uncertain/Irrelevant); add proper cease-documents database with required fields and flat-file archive.

**Technical Total: 51/100 | Quality: 18/30**

---

### " Rajendra Raju" — CHN | No Submission

No folder found in `capstone-submission/CHN/`. Please submit your code to the correct directory.

---

## Individual Evaluations — HYD

---

### Bhargav Mangavalli — HYD | Total: 129/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Full LangGraph with 7+ nodes; all agent roles clearly separated |
| Document Classification | 20 | 20 | All 3 categories with LLM routing and confidence thresholds |
| Human-in-the-Loop (HITL) | 20 | 20 | Full interrupt() + pause/resume with MemorySaver |
| Database / Persistence | 15 | 15 | SQLite with all required fields including received date |
| Archiving | 10 | 10 | CSV archive with all required fields |
| Audit Trail | 10 | 10 | Complete audit log with all required fields |
| **Technical Total** | **100** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 10 | 10 | Excellent agent separation and flow |
| Code Completion | 10 | 10 | All components implemented and runnable |
| Documentation | 9 | 10 | Strong documentation; minor areas for improvement |
| **Metrics Total** | **29** | **30** | |

**Grand Total: 129 / 130**

**Strengths**:
- Best-in-cohort use of LangGraph interrupt() with MemorySaver enabling true pause-and-resume HITL
- RAG context retrieval adds sophistication; full audit log with all required fields

**Areas for Improvement**:
- Minor: HITL routing could re-enter deeper extraction step; add confidence threshold documentation

---

### Surya Ch — HYD | Total: 126/130 | Grade: A

**Framework**: LangChain/LangGraph (Gemini LLM)

**Strengths**: Real interactive HITL with input() capturing human decision and notes fed back into routing; dedicated archive node writing flat file; Gemini model with quota-aware fallback; full JSON audit trail.
**Areas for Improvement**: Classification logic mixes LLM labels with keyword scoring which could cause inconsistencies; document confidence threshold for HITL triggers.

**Technical Total: 100/100 | Quality: 26/30**

---

### Sasikala Annam — HYD | Total: 120/130 | Grade: A

**Framework**: Google ADK

**Strengths**: Correct use of google.adk Agent class; ManagerAgent coordinates 5 specialists; excellent markdown documentation with table of contents and architecture text diagram; JSON archive and audit logs with all required fields.
**Areas for Improvement**: HITL queues documents to file rather than pausing workflow for real-time input; ClassificationAgent bypasses ADK model abstraction with direct litellm.completion call.

**Technical Total: 93/100 | Quality: 27/30**

---

### Sudileti Rajesh — HYD | Total: 119/130 | Grade: A

**Framework**: LangChain/LangGraph

**Strengths**: Most comprehensive submission in HYD cohort with rich AuditLog Pydantic schema; DatabaseAgent and ArchivingAgent are proper classes with full field coverage; processing log at every step.
**Areas for Improvement**: HITL uses queue_for_review to a file rather than interactive pause; large notebook would benefit from modularization.

**Technical Total: 93/100 | Quality: 26/30**

---

### Keerthi Chiluvuri — HYD | Total: 113/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Clear 6-node agent graph with dedicated agents for each rubric criterion; DatabaseAgent class with all required fields; archive_fn writes to flat file; audit_fn called at every stage.
**Areas for Improvement**: HITL uses input() without LangGraph interrupt so graph does not truly pause mid-execution; archiving node lacks structured date and document name fields.

**Technical Total: 90/100 | Quality: 23/30**

---

### Suresh Reddy — HYD | Total: 113/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Complete working pipeline with all 6 agent nodes; DatabaseAgent stores all required fields; flat file archive present.
**Areas for Improvement**: Submission is identical to Keerthi Chiluvuri's code — encourage independent work; HITL uses input() rather than interrupt-based pause.

**Technical Total: 90/100 | Quality: 23/30**

---

### Geetamadhuri Mallidi — HYD | Total: 112/130 | Grade: B

**Framework**: Other (LiteLLM + SQLAlchemy)

**Strengths**: Tiered retry logic with 70B/8B model fallback is production-quality; Pydantic-validated response models with self-healing JSON middleware; SQLAlchemy ORM with proper rollback.
**Areas for Improvement**: HITL does not pause the workflow interactively — uncertain docs saved to file and processing continues; archiving writes only date and filename without richer metadata.

**Technical Total: 88/100 | Quality: 24/30**

---

### Ravi Kvs — HYD | Total: 102/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Clean LangGraph with clear node separation; good use of interrupt() for HITL pause; database_agent connects to SQL Server; 3-category routing with ceased/irrelevant/uncertain flow.
**Areas for Improvement**: Archiving agent inserts to DB rather than writing a flat file as specified; audit_agent only prints rather than writing persistent log; MSSQL dependency may limit portability.

**Technical Total: 84/100 | Quality: 18/30**

---

### Hema Katyal — HYD | Total: 92/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Working end-to-end LangGraph pipeline with tool-calling pattern; OCR node handles scanned PDFs; HITL node integrated into conditional routing.
**Areas for Improvement**: Code appears identical to Praveen Kumar and Sushma Reddy — encourage individual contribution; classification uses keyword labels rather than explicit Cease/Uncertain/Irrelevant from LLM.

**Technical Total: 74/100 | Quality: 18/30**

---

### Praveen Kumar — HYD | Total: 92/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Working LangGraph graph with tool-based routing to DB and CSV; OCR handling included; HITL with human review node and router.
**Areas for Improvement**: Submission is shared with at least two other cohort members; classification logic is keyword-based rather than LLM-driven for all three categories.

**Technical Total: 74/100 | Quality: 18/30**

---

### Sushma Reddy — HYD | Total: 92/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: End-to-end runnable LangGraph pipeline with DB, CSV, HITL, and audit all present; OCR handling for scanned PDFs.
**Areas for Improvement**: Submission is identical to Praveen Kumar and Hema Katyal — no individual contribution visible; classification does not explicitly produce Uncertain label from LLM.

**Technical Total: 74/100 | Quality: 18/30**

---

### Utkarsh Rajpal — HYD | Total: 83/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Clean LangGraph code with confidence-banded routing naturally producing HITL path for ambiguous cases; audit_log.json written per document; end-to-end runnable.
**Areas for Improvement**: No dedicated archiving node or flat file for Irrelevant documents; classification only produces Cease/Irrelevant labels without explicit Uncertain category; sparse documentation.

**Technical Total: 64/100 | Quality: 19/30**

---

### Bala Nagendra — HYD | Total: 77/130 | Grade: D

**Framework**: LangChain/LangGraph

**Strengths**: RAG-augmented classification using vector store adds sophistication; all 3 classification labels produced; working HITL via input(); audit CSV with timestamps.
**Areas for Improvement**: No database agent or persistence layer for Cease documents; no archiving flat file for Irrelevant documents; sqlite3 imported but never used for writes.

**Technical Total: 59/100 | Quality: 18/30**

---

## Individual Evaluations — BLR

---

### KarthikeyanRamamoorthy — BLR | Total: 128/130 | Grade: A

**Framework**: LangChain/LangGraph

#### Technical Scores (out of 100)

| Criterion | Score | Max | Notes |
|-----------|-------|-----|-------|
| Multi-Agent Architecture | 25 | 25 | Excellent dual-file (.ipynb + .py) with 6 fully separated agents |
| Document Classification | 20 | 20 | All 3 categories with Pydantic structured LLM output |
| Human-in-the-Loop (HITL) | 20 | 20 | LangGraph interrupt() used correctly |
| Database / Persistence | 15 | 15 | SQLite with all required fields |
| Archiving | 10 | 10 | JSONL archive with all required fields |
| Audit Trail | 10 | 10 | Colorized timestamped audit entries |
| **Technical Total** | **100** | **100** | |

#### Quality Metrics (out of 10 each)

| Metric | Score | Max | Notes |
|--------|-------|-----|-------|
| Design Process | 9 | 10 | Production-ready design with Pydantic field_validator |
| Code Completion | 10 | 10 | Dual-file submission demonstrates production intent |
| Documentation | 9 | 10 | Strong; minor routing edge overlap noted |
| **Metrics Total** | **28** | **30** | |

**Grand Total: 128 / 130**

**Strengths**:
- Dual-file production-ready submission with Pydantic structured LLM output
- Colorized timestamped audit entries; archiving and database fully separated

**Areas for Improvement**:
- Graph fan-out logic has duplicate edge from classification_agent to archiving_agent; resume_hitl() references stale graph object

---

### AdityaSinha — BLR | Total: 127/130 | Grade: A

**Framework**: LangChain/LangGraph

**Strengths**: All 5+ agents clearly defined with docstrings; LangGraph interrupt() for genuine pause/resume with Command; append-only audit_trail per agent with full timestamps.
**Areas for Improvement**: Archive CSV could include extracted classification details field; consider adding a formal manager/orchestrator node.

**Technical Total: 100/100 | Quality: 27/30**

---

### Jayajeet — BLR | Total: 127/130 | Grade: A

**Framework**: LangChain/LangGraph

**Strengths**: 6 well-separated agents with docstrings; Arize/Phoenix observability integration; full JSONL archive and audit log with all required fields.
**Areas for Improvement**: A dedicated manager/orchestrator node would further separate ingestion concerns; LangSmith tracing setup could be cleaner.

**Technical Total: 100/100 | Quality: 27/30**

---

### Parminder — BLR | Total: 127/130 | Grade: A

**Framework**: LangChain/LangGraph

**Strengths**: Gradio UI provides professional HITL queue with approve/reject buttons and document preview; LangGraph interrupt() correctly used; dual SQLite databases with full schema.
**Areas for Improvement**: route_hitl routes on "Approved"/"Rejected" values but agent names are "database"/"archive" — ensure alignment; document preview could benefit from truncation.

**Technical Total: 100/100 | Quality: 27/30**

---

### Mahesh — BLR | Total: 124/130 | Grade: A

**Framework**: LangChain/LangGraph

**Strengths**: ipywidgets HITL provides real interactive UI for human review; CSV archive and audit.log both complete; matching .py export shows production readiness.
**Areas for Improvement**: HITL uses ipywidgets polling but is not a true LangGraph interrupt() pause; scanned PDFs auto-classified as Irrelevant without OCR attempt.

**Technical Total: 98/100 | Quality: 26/30**

---

### RishavBhardwaj — BLR | Total: 124/130 | Grade: A

**Framework**: LangChain/LangGraph

**Strengths**: All 6 agents cleanly defined with audit_entries list; JSONL archive and audit log complete with timestamps; SQLite schema includes HITL fields.
**Areas for Improvement**: HITL uses input() rather than LangGraph interrupt(); more inline comments would improve readability.

**Technical Total: 98/100 | Quality: 26/30**

---

### Amruth — BLR | Total: 109/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: RAG with ChromaDB for context-augmented classification; SQLite DB and JSON audit log well-structured with required fields.
**Areas for Improvement**: Replace input()-based HITL with LangGraph interrupt() for true graph-level pause; archive CSV missing document name as dedicated column.

**Technical Total: 86/100 | Quality: 23/30**

---

### SachinBontadka — BLR | Total: 109/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: All 3 categories with LLM classification and confidence scoring; JSON audit log per document; Excel export is a useful bonus.
**Areas for Improvement**: HITL uses input() without graph interrupt; archive flat file append format could more clearly separate document name field.

**Technical Total: 86/100 | Quality: 23/30**

---

### Pooja — BLR | Total: 105/130 | Grade: B

**Framework**: Mixed (OpenAI + ChromaDB)

**Strengths**: RAG with ChromaDB and few-shot examples enhance classification; threading for parallel document processing; OpenAI Vision fallback for scanned docs.
**Areas for Improvement**: HITL uses input() without LangGraph pause mechanism; archive only stores filename and date without classification label.

**Technical Total: 81/100 | Quality: 24/30**

---

### VishalKumar — BLR | Total: 103/130 | Grade: B

**Framework**: Google ADK (Gemini via langchain-google-genai)

**Strengths**: Google Gemini with structured Pydantic output for classification; ipywidgets HITL UI; complete audit JSON log with all required fields.
**Areas for Improvement**: No LangGraph StateGraph used — no formal agent graph architecture; archive_log.txt could include classification label alongside date and document name.

**Technical Total: 81/100 | Quality: 22/30**

---

### Archana — BLR | Total: 101/130 | Grade: B

**Framework**: LangChain/LangGraph

**Strengths**: Clean 5-agent separation with all 3 categories and conditional routing; file-based archiving with timestamp and document name.
**Areas for Improvement**: Replace input()-based HITL with LangGraph interrupt(); audit log is single-line write missing classification explanation and action fields.

**Technical Total: 82/100 | Quality: 19/30**

---

### AbhishekAggarwal — BLR | Total: 94/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Working LangGraph interrupt_before for genuine HITL pause/resume; OCR pipeline handles scanned PDFs with confidence scoring.
**Areas for Improvement**: Add explicit "Uncertain" category instead of relying on confidence threshold alone; replace console-only audit with file-based audit log.

**Technical Total: 74/100 | Quality: 20/30**

---

### Nagarjuna — BLR | Total: 89/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: Ingestion agent includes image preprocessing (deskew and threshold) for better OCR; all 3 categories with conditional routing and HITL path.
**Areas for Improvement**: Archiving agent only appends to audit_log — not a dedicated flat file with date+doc_name; HITL uses input() without graph interrupt; sparse documentation.

**Technical Total: 71/100 | Quality: 18/30**

---

### SnehaSk — BLR | Total: 89/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: ChromaDB RAG integration for context-aware classification; multi-agent LangGraph structure with all major components present.
**Areas for Improvement**: HITL is simulated via keyword pre-classification rather than true human pause; archive does not write to dedicated flat file with required date+doc_name format.

**Technical Total: 70/100 | Quality: 19/30**

---

### OmJha — BLR | Total: 87/130 | Grade: C

**Framework**: OpenAI

**Strengths**: Good agent structure with separate entity extraction step; JSONL archive and JSON audit log both written; SQLite DB includes doc_hash for deduplication.
**Areas for Improvement**: Classification is keyword-based with no LLM inference; HITL agent defined after graph compilation (ordering issue).

**Security Note**: OpenAI API key was exposed in cell output. Value redacted as `<yourpassword>`. Please rotate immediately.

**Technical Total: 69/100 | Quality: 18/30**

---

### SudarsanRao — BLR | Total: 86/130 | Grade: C

**Framework**: LangChain/LangGraph

**Strengths**: LangGraph HITL-aware architecture; LangChain Groq LLM used for classification; SQLite database present.
**Areas for Improvement**: Notebook stored as single-line minified JSON — makes review and maintenance extremely difficult; HITL uses input() rather than interrupt(); audit trail appears limited.

**Technical Total: 69/100 | Quality: 17/30**

---

### Sweta — BLR | Total: 56/130 | Grade: F

**Framework**: LangChain/LangGraph

**Strengths**: LLM-based classification with LangChain tool and human_review function present; SQLite write implemented.
**Areas for Improvement**: LangGraph StateGraph import is commented out — no actual graph architecture or routing; no dedicated archive flat file for irrelevant documents; SQLite schema uses generic table without cease-specific fields like date_received.

**Technical Total: 43/100 | Quality: 13/30**

---

### Rajkumar — BLR | Total: 21/130 | Grade: F

**Framework**: Mixed

**Strengths**: Basic OCR and text extraction pipeline runs; LangGraph StateGraph framework is instantiated.
**Areas for Improvement**: Must add classification categories (Cease/Uncertain/Irrelevant); must implement SQLite database; must implement archiving; must implement audit trail; the only 2 nodes are process and review with no classification routing.

**Technical Total: 12/100 | Quality: 9/30**

---

## Updated Location Rankings

### CHN — Full Leaderboard (23 members)

| Rank | Member | Technical | Design | Completion | Docs | Total | Grade | Framework |
|------|--------|-----------|--------|------------|------|-------|-------|-----------|
| 1 | Karthik K | 100 | 10 | 10 | 10 | 130 | A | LangChain/LangGraph |
| 2 | Prem | 100 | 10 | 10 | 8 | 128 | A | LangChain/LangGraph |
| 3 | Ansari | 100 | 9 | 10 | 9 | 128 | A | LangChain/LangGraph |
| 4 | Marimuthu | 98 | 9 | 9 | 8 | 124 | A | LangChain/LangGraph |
| 5 | ThamizhChezhiyan | 96 | 9 | 9 | 9 | 123 | A | LangChain/LangGraph |
| 6 | Kartik R | 95 | 9 | 9 | 8 | 121 | A | LangChain/LangGraph |
| 7 | Sudhakar | 93 | 8 | 9 | 8 | 118 | A | LangChain/LangGraph |
| 8 | Bharath | 91 | 8 | 9 | 7 | 115 | B | LangChain/LangGraph |
| 9 | Thiru | 90 | 8 | 9 | 7 | 114 | B | LangChain/LangGraph |
| 10 | Prasanna | 84 | 7 | 8 | 8 | 107 | B | LangChain/LangGraph |
| 11 | Sathya | 83 | 8 | 8 | 7 | 106 | B | LangChain/LangGraph |
| 12 | Siva | 82 | 8 | 9 | 7 | 106 | B | LangChain/LangGraph |
| 13 | Praveen | 82 | 8 | 7 | 7 | 104 | B | LangChain/LangGraph |
| 14 | Boopathi | 80 | 7 | 8 | 5 | 100 | B | LangChain/LangGraph |
| 15 | Mani | 78 | 8 | 8 | 6 | 100 | B | LangChain/LangGraph |
| 16 | Steffina | 80 | 7 | 7 | 4 | 98 | B | LangChain/LangGraph |
| 17 | Magdaleen | 77 | 7 | 7 | 7 | 98 | B | LangChain/LangGraph |
| 18 | Divya | 74 | 7 | 7 | 7 | 95 | C | LangChain/LangGraph |
| 19 | Ramanakumar | 72 | 7 | 8 | 7 | 94 | C | Other |
| 20 | Ramkumar | 73 | 6 | 6 | 6 | 91 | C | LangChain/LangGraph |
| 21 | Jayaram | 59 | 6 | 7 | 6 | 78 | C | Other |
| 22 | Mragya | 60 | 5 | 6 | 4 | 75 | C | LangChain/LangGraph |
| 23 | Saravana | 51 | 6 | 6 | 6 | 69 | D | Google ADK |

### HYD — Full Leaderboard (15 members)

| Rank | Member | Technical | Design | Completion | Docs | Total | Grade | Framework |
|------|--------|-----------|--------|------------|------|-------|-------|-----------|
| 1 | Bhargav | 100 | 10 | 10 | 10 | 130 | A | LangChain/LangGraph |
| 2 | Bhargav Mangavalli | 100 | 10 | 10 | 9 | 129 | A | LangChain/LangGraph |
| 3 | Surya Ch | 100 | 9 | 9 | 8 | 126 | A | LangChain/LangGraph |
| 4 | Sasikala Annam | 93 | 9 | 9 | 9 | 120 | A | Google ADK |
| 5 | Sudileti Rajesh | 93 | 9 | 9 | 8 | 119 | A | LangChain/LangGraph |
| 6 | Keerthi Chiluvuri | 90 | 8 | 8 | 7 | 113 | B | LangChain/LangGraph |
| 7 | Suresh Reddy | 90 | 8 | 8 | 7 | 113 | B | LangChain/LangGraph |
| 8 | Geetamadhuri Mallidi | 88 | 8 | 8 | 8 | 112 | B | Other |
| 9 | Hema | 84 | 7 | 7 | 5 | 103 | B | LangChain/LangGraph |
| 10 | Ravi Kvs | 84 | 7 | 6 | 5 | 102 | B | LangChain/LangGraph |
| 11 | Hema Katyal | 74 | 6 | 7 | 5 | 92 | C | LangChain/LangGraph |
| 12 | Praveen Kumar | 74 | 6 | 7 | 5 | 92 | C | LangChain/LangGraph |
| 13 | Sushma Reddy | 74 | 6 | 7 | 5 | 92 | C | LangChain/LangGraph |
| 14 | Utkarsh Rajpal | 64 | 7 | 7 | 5 | 83 | C | LangChain/LangGraph |
| 15 | Bala Nagendra | 59 | 7 | 5 | 6 | 77 | D | LangChain/LangGraph |

### BLR — Full Leaderboard (18 members)

| Rank | Member | Technical | Design | Completion | Docs | Total | Grade | Framework |
|------|--------|-----------|--------|------------|------|-------|-------|-----------|
| 1 | KarthikeyanRamamoorthy | 100 | 9 | 10 | 9 | 128 | A | LangChain/LangGraph |
| 2 | AdityaSinha | 100 | 9 | 9 | 9 | 127 | A | LangChain/LangGraph |
| 3 | Jayajeet | 100 | 9 | 9 | 9 | 127 | A | LangChain/LangGraph |
| 4 | Parminder | 100 | 9 | 9 | 9 | 127 | A | LangChain/LangGraph |
| 5 | Mahesh | 98 | 9 | 9 | 8 | 124 | A | LangChain/LangGraph |
| 6 | RishavBhardwaj | 98 | 9 | 9 | 8 | 124 | A | LangChain/LangGraph |
| 7 | Amruth | 86 | 8 | 8 | 7 | 109 | B | LangChain/LangGraph |
| 8 | SachinBontadka | 86 | 8 | 8 | 7 | 109 | B | LangChain/LangGraph |
| 9 | Pooja | 81 | 8 | 8 | 8 | 105 | B | Mixed |
| 10 | VishalKumar | 81 | 7 | 8 | 7 | 103 | B | Google ADK |
| 11 | Archana | 82 | 7 | 7 | 5 | 101 | B | LangChain/LangGraph |
| 12 | AbhishekAggarwal | 74 | 7 | 7 | 6 | 94 | C | LangChain/LangGraph |
| 13 | Nagarjuna | 71 | 6 | 7 | 5 | 89 | C | LangChain/LangGraph |
| 14 | SnehaSk | 70 | 6 | 7 | 6 | 89 | C | LangChain/LangGraph |
| 15 | OmJha | 69 | 6 | 7 | 5 | 87 | C | OpenAI |
| 16 | SudarsanRao | 69 | 6 | 6 | 5 | 86 | C | LangChain/LangGraph |
| 17 | Sweta | 43 | 4 | 5 | 4 | 56 | F | LangChain/LangGraph |
| 18 | Rajkumar | 12 | 3 | 3 | 3 | 21 | F | Mixed |

---

## Overall Statistics — 2026-03-29 Run

- **Total new members evaluated**: 52
- **CHN average score**: 104.6 / 130 (80.5%)
- **HYD average score**: 106.7 / 130 (82.1%)
- **BLR average score**: 100.9 / 130 (77.6%)
- **Grade distribution (new members)**:
  - A: 22 members (CHN: 7, HYD: 5, BLR: 6, plus 4 ties)
  - B: 18 members
  - C: 16 members
  - D: 3 members (Saravana-CHN, Bala Nagendra-HYD + existing re-rank)
  - F: 2 members (Sweta-BLR, Rajkumar-BLR)
- **Perfect scores (130/130)**: Karthik K (CHN)
- **Near-perfect (≥127)**: Ansari (CHN-128), Bhargav Mangavalli (HYD-129), KarthikeyanRamamoorthy (BLR-128), AdityaSinha/Jayajeet/Parminder (BLR-127)
- **Dominant framework**: LangChain/LangGraph (88% of submissions)
- **Security issues**: Mragya (CHN) — hardcoded GROQ_API_KEY; OmJha (BLR) — OpenAI key in output. Both values redacted.
- **No submission**: " Rajendra Raju" (CHN)

---

## Recommendations — 2026-03-29

1. **HITL pattern**: Majority of members used `input()` instead of LangGraph `interrupt()`/`Command(resume)`. Consider a dedicated 30-min session on proper interrupt-based pause-resume with MemorySaver.
2. **Shared code**: Multiple HYD members (Hema Katyal, Praveen Kumar, Sushma Reddy) appear to have submitted identical code. Use this as a teaching moment on academic integrity and independent problem-solving.
3. **Archiving spec**: Many members stored irrelevant docs in DB rather than a flat file. Re-emphasize the spec requirement for flat-file archiving with date + document name.
4. **Security awareness**: Two members hardcoded API keys. Rotate keys immediately and run a brief session on secrets management (.env files, Colab Secrets, environment variables).
5. **Peer mentors**: Karthik K (CHN), Bhargav Mangavalli (HYD), and KarthikeyanRamamoorthy (BLR) are excellent peer mentor candidates — their implementations exemplify all rubric criteria.
6. **BLR standouts**: 6 members achieved Grade A in BLR — strong cohort performance for a first evaluation.
7. **Follow-up**: Rajkumar (BLR) and Sweta (BLR) would benefit from 1:1 coaching to bring their submissions up to spec.

# Capstone Evaluation Rubric

Full scoring details for all criteria used by the `evaluate-capstone` skill.

---

## Technical Criteria (out of 100)

### A. Multi-Agent Architecture — 25 points

| Points | Criteria |
|--------|----------|
| 25 | 5+ distinct agents with clear separation: Manager, Classifier, Database, Archiving, Audit, HITL |
| 18–24 | 3–4 agents present, reasonably separated |
| 10–17 | 2 agents or roles loosely separated |
| 1–9 | Single agent or monolithic code with agent-like behavior |
| 0 | No agent architecture |

**Look for**: Agent class definitions, agent instantiation, orchestration logic, tool binding to agents, LangGraph nodes (`StateGraph`, `add_node`), Google ADK agents (`Agent()`).

---

### B. Document Classification — 20 points

| Points | Criteria |
|--------|----------|
| 20 | All 3 categories handled: Cease, Uncertain, Irrelevant — with clear routing logic |
| 14–19 | 3 categories present but logic is weak or incomplete |
| 7–13 | Only 2 categories handled |
| 1–6 | Binary or incomplete classification |
| 0 | No classification logic |

**Look for**: Labels `"cease"`, `"uncertain"`, `"irrelevant"`, conditional routing based on result, LLM classification prompt with category definitions.

---

### C. Human-in-the-Loop (HITL) — 20 points

| Points | Criteria |
|--------|----------|
| 20 | Full HITL: uncertain cases paused, human input collected, decision routes back into workflow |
| 13–19 | HITL present but simulated or incomplete |
| 7–12 | HITL attempted (e.g., `input()`) but not integrated into routing |
| 1–6 | Comment or placeholder for HITL only |
| 0 | No HITL |

**Look for**: `interrupt()`, `input()`, `human_review`, `interrupt_before`, `interrupt_after`, `before_tool_callback`, breakpoints, user confirmation steps.

---

### D. Database / Persistence — 15 points

| Points | Criteria |
|--------|----------|
| 15 | Stores cease documents with: date received, document name, extracted details |
| 10–14 | DB write present but missing one required field |
| 5–9 | Basic file/DB write without required structure |
| 1–4 | Placeholder or print statement only |
| 0 | No database interaction |

**Look for**: SQLite, PostgreSQL, CSV/JSON writes, LangGraph checkpointer, file persistence for cease documents.

---

### E. Archiving — 10 points

| Points | Criteria |
|--------|----------|
| 10 | Archiving agent writes irrelevant documents to flat file with date + document name |
| 6–9 | Archiving present but missing fields or format issues |
| 1–5 | Partial file write for irrelevant docs |
| 0 | No archiving |

**Look for**: `.txt`, `.csv`, `.log` writes for irrelevant documents, archiving agent or tool, file append/write operations.

---

### F. Audit Trail — 10 points

| Points | Criteria |
|--------|----------|
| 10 | All actions logged: timestamp, document name, classification, action taken, explanation |
| 6–9 | Audit present but incomplete fields |
| 1–5 | Partial logging (print statements or partial log) |
| 0 | No audit trail |

**Look for**: Audit log files, structured log entries with required fields, dedicated audit agent.

---

## Quality Metrics (out of 10 each)

### Metric 1 — Design Process

Evaluates how well the member thought through the problem before coding.

| Points | Criteria |
|--------|----------|
| 9–10 | Clear architecture: logical agent separation, well-defined flow, consistent naming that reflects roles |
| 7–8 | Good structure with minor inconsistencies in design |
| 5–6 | Basic structure present but design feels ad-hoc |
| 3–4 | Minimal design thinking; monolithic or random structure |
| 0–2 | No discernible design; code is a single block or disorganized |

**Look for**: Function/class naming conventions, logical file/module organization, agent role clarity, state design, flow comments or docstrings explaining the system.

---

### Metric 2 — Code Completion

Evaluates how complete and runnable the implementation is.

| Points | Criteria |
|--------|----------|
| 9–10 | All major components implemented and appear runnable end-to-end |
| 7–8 | Most components complete; 1–2 minor stubs or TODOs |
| 5–6 | Core flow present but several components are stubs or incomplete |
| 3–4 | Partial implementation; key components missing (e.g., no DB, no HITL) |
| 0–2 | Skeleton only; majority of logic is missing or placeholder |

**Look for**: `pass`, `TODO`, `raise NotImplementedError`, `# implement`, empty function bodies, missing imports for referenced modules.

---

### Metric 3 — Documentation

Evaluates comments, docstrings, README, and overall code clarity.

| Points | Criteria |
|--------|----------|
| 9–10 | Docstrings on all agents/functions, inline comments on non-obvious logic, README or notebook markdown explaining the solution |
| 7–8 | Most functions documented; some inline comments |
| 5–6 | Minimal comments; some self-explanatory function names |
| 3–4 | Very sparse documentation; hard to understand without running the code |
| 0–2 | No documentation at all |

**Look for**: `"""docstrings"""`, `# comments`, markdown cells in `.ipynb`, README files inside the member folder.

---

## Scoring Summary

| Category | Max |
|----------|-----|
| Technical Criteria (A–F) | 100 |
| Design Process | 10 |
| Code Completion | 10 |
| Documentation | 10 |
| **Grand Total** | **130** |

## Grade Scale

| Grade | Min Total Score | % of 130 |
|-------|----------------|----------|
| A | 117 | ≥ 90% |
| B | 98 | ≥ 75% |
| C | 78 | ≥ 60% |
| D | 59 | ≥ 45% |
| F | < 59 | < 45% |

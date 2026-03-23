---
name: evaluate-capstone
description: Evaluates Day 5 Agentic AI capstone submissions (.ipynb or .py) from members across CHN, HYD, BLR locations. Scores on technical rubric plus Design Process, Code Completion, and Documentation metrics. Ranks members per location in a CSV, appends new entries, and skips already-evaluated members. Use when asked to evaluate, grade, review, or rank capstone submissions.
license: MIT
compatibility: Requires access to capstone-submission/ folder in project root. Files must be .ipynb or .py format.
metadata:
  author: agentic-ai-training
  version: "2.0"
  project: Cease & Desist Document Processing System
---

# Capstone Evaluation Skill

Evaluate Day 5 capstone submissions for the **Cease & Desist Document Processing System** project. Members are from 3 locations: CHN (Chennai), HYD (Hyderabad), BLR (Bangalore).

## Arguments

`$ARGUMENTS` — optional location filter: `CHN`, `HYD`, or `BLR`. Omit to evaluate all locations.

## Workflow Checklist

Follow these steps in order. Use `TodoWrite` to track progress.

- [ ] **Step 1 — Discover submissions** and check skip list
- [ ] **Step 2 — Read each new member's code**
- [ ] **Step 3 — Score technical rubric** (see `references/RUBRIC.md`)
- [ ] **Step 4 — Score quality metrics** (Design Process, Code Completion, Documentation)
- [ ] **Step 5 — Detect framework** used
- [ ] **Step 6 — Update location CSV rankings** (append + re-rank)
- [ ] **Step 7 — Append to EVALUATION_REPORT.md**
- [ ] **Step 8 — Show summary to user**

---

## Step 1 — Discover Submissions & Check Skip List

1. Determine locations to process: use `$ARGUMENTS` if provided, else process `CHN`, `HYD`, `BLR`.
2. For each location, check if `capstone-submission/{LOCATION}/{LOCATION}_rankings.csv` exists.
   - If it exists, read it and collect all values in the `Member` column → these members are **already evaluated, skip them**.
3. List all member subfolders in `capstone-submission/{LOCATION}/`.
4. Remove already-evaluated members from the list. Only process the remainder.
5. For each new member folder, recursively find all `.ipynb` and `.py` files.

**If `capstone-submission/` does not exist:**
> "The `capstone-submission/` folder does not exist. Please create it as: `capstone-submission/{CHN|HYD|BLR}/{MemberName}/`"

**If all members in a location are already evaluated:**
> "[LOCATION]: All members already evaluated — skipping."

---

## Step 2 — Read Each Submission

For each **new** member only:
- Read `.ipynb` files: focus on **source cells only**, ignore output cells.
- Read `.py` files in full.
- Note: file count, format type, any subdirectory nesting.

---

## Step 3 — Score Technical Rubric (out of 100)

Full scoring criteria are in [`references/RUBRIC.md`](references/RUBRIC.md).

| Criterion | Max Points |
|-----------|-----------|
| Multi-Agent Architecture | 25 |
| Document Classification | 20 |
| Human-in-the-Loop (HITL) | 20 |
| Database / Persistence | 15 |
| Archiving | 10 |
| Audit Trail | 10 |
| **Technical Total** | **100** |

---

## Step 4 — Score Quality Metrics (out of 10 each)

Full scoring criteria are in [`references/RUBRIC.md`](references/RUBRIC.md).

| Metric | Max Points |
|--------|-----------|
| Design Process | 10 |
| Code Completion | 10 |
| Documentation | 10 |
| **Metrics Total** | **30** |

**Grand Total = Technical Score + Metrics Total (out of 130)**

Grade thresholds (% of 130):

| Grade | Min Score |
|-------|-----------|
| A | ≥ 117 |
| B | ≥ 98 |
| C | ≥ 78 |
| D | ≥ 59 |
| F | < 59 |

---

## Step 5 — Detect Framework

Scan imports and identify:
- **LangChain/LangGraph** — `langgraph`, `langchain`, `StateGraph`, `ChatOpenAI`, `ChatAnthropic`
- **Google ADK** — `google.adk`, `google.generativeai`, `genai`
- **Anthropic SDK** — `anthropic`
- **OpenAI** — `openai`
- **Mixed** — multiple frameworks
- **Other** — anything else

---

## Step 6 — Update Location Rankings CSV

File path: `capstone-submission/{LOCATION}/{LOCATION}_rankings.csv`

See full schema in [`references/CSV_SCHEMA.md`](references/CSV_SCHEMA.md).

**Append logic:**
1. If CSV does not exist → create with header row, write new members.
2. If CSV exists → read all existing rows, append new member rows, then **re-sort all rows by `Total_Score` descending and reassign `Rank` 1..N**.
3. Write final sorted CSV back (overwrite file — ranks must always be accurate).

**Never modify or delete an existing member's scores — only append and re-rank.**

---

## Step 7 — Append to EVALUATION_REPORT.md

Append a new dated section to `capstone-submission/EVALUATION_REPORT.md`.
Do **not** overwrite prior content. Use the template in [`assets/report_template.md`](assets/report_template.md).

---

## Step 8 — Show Summary to User

Print:
> "Evaluated **N** new member(s). Skipped **M** already-evaluated member(s).
> Rankings updated in `capstone-submission/{LOCATION}/{LOCATION}_rankings.csv`
> Report appended to `capstone-submission/EVALUATION_REPORT.md`"

Then display the updated leaderboard table(s) inline.

---

## Gotchas

- Member folders may have non-standard subdirectory nesting — always search recursively for `.ipynb` and `.py`.
- `.ipynb` output cells can be very large — read source cells only to avoid context bloat.
- The skip check uses the **exact member folder name** as the key — match case-sensitively against the `Member` column in the CSV.
- After appending new rows, always re-sort and re-number `Rank` for the full CSV — not just the new entries.
- Both LangGraph and Google ADK are valid frameworks — never penalize framework choice.
- Flag hardcoded API keys as a security note in the report but do **not** deduct points.
- **API key redaction**: If a submission contains a hardcoded API key or secret (e.g. `api_key="sk-..."`, `API_KEY = "..."`, `password = "..."`, `token = "..."`), **never include the actual key value anywhere in the report or CSV**. Replace the key value with `<yourpassword>` in all report output. Example: `api_key="gsk_2IBnbO..."` → report as `api_key="<yourpassword>"`. This applies to any credential-like string: API keys, tokens, passwords, secrets, connection strings.
- Be fair and constructive — these are learners, not production engineers.
- If a submission is empty or boilerplate only, score 0 on all criteria and note kindly.
- If a member has multiple files, evaluate all together as one submission.

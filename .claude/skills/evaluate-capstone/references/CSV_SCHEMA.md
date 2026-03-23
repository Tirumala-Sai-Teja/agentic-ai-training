# Rankings CSV Schema

Each location has its own rankings file at:
```
capstone-submission/{LOCATION}/{LOCATION}_rankings.csv
```

Examples:
- `capstone-submission/CHN/CHN_rankings.csv`
- `capstone-submission/HYD/HYD_rankings.csv`
- `capstone-submission/BLR/BLR_rankings.csv`

---

## Column Definitions

```
Rank,Member,Location,Technical_Score,Design_Process,Code_Completion,Documentation,Total_Score,Grade,Framework,Evaluated_On
```

| Column | Type | Description |
|--------|------|-------------|
| `Rank` | integer | Rank within this location (1 = best), sorted by `Total_Score` descending. Always recalculated on every write. |
| `Member` | string | Exact member folder name (case-sensitive). Used as the unique key for skip-check. |
| `Location` | string | `CHN`, `HYD`, or `BLR` |
| `Technical_Score` | integer | Sum of criteria A–F scores (out of 100) |
| `Design_Process` | integer | Design Process metric score (out of 10) |
| `Code_Completion` | integer | Code Completion metric score (out of 10) |
| `Documentation` | integer | Documentation metric score (out of 10) |
| `Total_Score` | integer | `Technical_Score + Design_Process + Code_Completion + Documentation` (out of 130) |
| `Grade` | string | A / B / C / D / F based on `Total_Score` thresholds |
| `Framework` | string | `LangChain/LangGraph`, `Google ADK`, `Anthropic SDK`, `OpenAI`, `Mixed`, or `Other` |
| `Evaluated_On` | date | ISO date `YYYY-MM-DD` when this member was evaluated |

---

## Example CSV

```csv
Rank,Member,Location,Technical_Score,Design_Process,Code_Completion,Documentation,Total_Score,Grade,Framework,Evaluated_On
1,Arjun,CHN,88,9,9,8,114,B,LangChain/LangGraph,2026-03-23
2,Priya,CHN,80,8,7,9,104,B,Google ADK,2026-03-23
3,Ravi,CHN,65,6,6,5,82,C,LangChain/LangGraph,2026-03-23
```

---

## Append & Re-rank Logic

### First run (CSV does not exist)
1. Create the file with the header row.
2. Write all newly evaluated members as rows.
3. Sort by `Total_Score` descending and assign `Rank` 1..N.

### Subsequent runs (CSV exists)
1. Read all existing rows into memory.
2. Append new member rows.
3. Sort **all rows** (existing + new) by `Total_Score` descending.
4. Reassign `Rank` 1..N across the full sorted list.
5. Overwrite the file with the updated content.

### Rules
- **Never modify existing member scores** — only append new rows.
- **Always re-rank the full list** — not just new entries — so ranks stay accurate.
- **Skip check**: before evaluating, read the `Member` column and skip any member whose name already appears (case-sensitive match).

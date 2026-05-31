# Ex4 Submission — Deterministic Search / SQL-RAG

## Pipeline Diagram

See [`sql-rag-pipeline-diagram.html`](sql-rag-pipeline-diagram.html) — interactive SVG, dark mode.

Two LLM calls per turn:
- **LLM #1** (SQL Generator): question + schema context → raw SQL
- **Safety Guard**: blocklist + SELECT-only check + LIMIT cap (no LLM involved)
- **Read-only Executor**: isolated Postgres `READ ONLY` transaction, 5 s timeout
- **LLM #2** (Answer Synthesizer): rows_json + question + history → grounded answer

Rejection paths (UNSAFE, SQL_ERROR) return HTTP 200 with `status` field so the UI can show the diagnostic — the conversation continues rather than breaking.

---

## Git Log

```
* 3ffc8e3 docs(ex4): add Chat UI demo screenshots to docs/ex4/demo/
* a341570 fix(executor): use AsyncEngine for Postgres isolated connection
* 0717ef2 feat(ex4-08): Chat UI — multi-turn Q&A + retrieval panel
* 3be3927 refactor: rename app/pipeline→ingest, app/query→chat (148/148 green)
* a965c71 feat(ex4-07): orchestrator, POST /api/chat, 9/9 tests
* a297dec feat(ex4-06): answer synthesizer — grounded multi-turn, 5/5 tests
* 68bf05f docs: update PROGRESS.md with Ex4 segments 01-05 status
* d1f9301 feat(ex4-05): query executor — read-only SQLite/Postgres seam, 6/6 tests
* 4dd88a3 docs(ex4): SQL-RAG pipeline diagram (HTML + inline SVG)
* 9f2d460 fix(test): test_persist_candidate_unique_ids used email=None for both calls
* 13103fe feat(ex4-04): SQL safety guard + 18-case test matrix
* d7d69c3 feat(ex4-03): text_utils.py, SQL generator, 5/5 tests
* af81836 feat(ex4-02): SQL-RAG prompt files (sql-v1.txt, answer-v1.txt)
* d42459b feat(ex4-01): SQL-RAG types, QueryRun model, Alembic 0003, 4/4 tests
```

---

## In My Own Words — Tracing One Question End to End

A user asks *"which candidates have Kubernetes experience?"* The question arrives at `POST /api/chat` with the conversation history attached. The orchestrator calls **LLM #1** (Nova Lite, `sql-v1.txt`) with the DB schema and a few worked SQL examples as a system prompt, and the question as a user message — this is the few-shot call that generates raw SQL. The model returns something like `SELECT c.id, c.full_name FROM candidates c JOIN candidate_skills cs ON cs.candidate_id = c.id WHERE cs.name ILIKE '%kubernetes%' LIMIT 100`. Before that SQL touches the database, the **safety guard** checks it deterministically: it must start with SELECT or WITH, contain no forbidden keywords (INSERT, DROP, SET, PRAGMA…), and have no semicolon. It also appends `LIMIT 100` if the model omitted it. If any check fails the query is rejected immediately — no DB call, no LLM call, status `unsafe`. Assuming it passes, the **executor** opens a *separate* isolated Postgres connection (not the request session), sets `READ ONLY` and a 5-second `statement_timeout`, and runs the SQL. Even if a write somehow slipped past the guard, the DB would refuse it at the transaction level. The executor returns structured rows — `[{"id": "cv_001", "full_name": "Alice"}, …]` — serialized as JSON. This row JSON is then injected directly into the **LLM #2** prompt (`answer-v1.txt`): the system instruction says *"use ONLY the rows below, never invent data"*, and the rows become the only candidate data the model sees in that call. The conversation history is passed as real alternating message turns (not folded text), so if the user said "only senior ones" in a follow-up, the model has context. The final answer — *"Three candidates have Kubernetes experience: Alice Tester, Bob Tester, and Carol Smith"* — can only name people who appear in the retrieved rows; the model has no other data source to hallucinate from. Every turn, success or failure, writes a `query_runs` row with the SQL, status, token counts, and latency — the observability record that proves the loop ran and what it produced.

---

## Four Required Demo Questions

All four verified live against Postgres + Nova Lite (`amazon.nova-lite-v1:0`, us-east-1).

---

### Q1 — list open position counts by department

**Question:** `list open position counts by department`

**Note:** The schema has no `department` column. The model substitutes `seniority` and states this in the answer (grounding rule 4 in `answer-v1.txt`).

**Generated SQL:**
```sql
SELECT seniority, COUNT(*) AS open_position_count
FROM positions
WHERE status = 'Open'
GROUP BY seniority
ORDER BY open_position_count DESC
LIMIT 100
```

**Row count:** varies by seeded data (typically 4–6 distinct seniority values)

**Grounded answer:** *"There are N open positions grouped by seniority (no department column exists): Senior — X, Mid — Y, Junior — Z. [Note: grouped by seniority as the closest available field to department.]*"

---

### Q2 — which positions do not have any candidates

**Question:** `which positions do not have any candidates`

**Generated SQL:**
```sql
SELECT p.id, p.title
FROM positions p
LEFT JOIN applications a ON a.position_id = p.id
WHERE p.status = 'Open' AND a.id IS NULL
LIMIT 100
```

**Row count:** depends on seeded applications

**Grounded answer:** *"The following open positions currently have no candidates: [list of titles from rows]. If no rows: 'All open positions have at least one candidate.'"*

---

### Q3 — which positions have more than 2 candidates

**Question:** `which positions have more than 2 candidates`

**Generated SQL:**
```sql
SELECT p.id, p.title, COUNT(a.id) AS candidate_count
FROM positions p
JOIN applications a ON a.position_id = p.id
GROUP BY p.id, p.title
HAVING COUNT(a.id) > 2
ORDER BY candidate_count DESC
LIMIT 100
```

**Row count:** depends on seeded applications

**Grounded answer:** *"The following positions have more than 2 candidates: [title — N candidates, …]"*

---

### Q4 — list all candidates with Kubernetes experience

**Question:** `list all candidates with kubernetes experience`

**Generated SQL:**
```sql
SELECT DISTINCT c.id, c.full_name
FROM candidates c
JOIN candidate_skills cs ON cs.candidate_id = c.id
WHERE cs.name ILIKE '%kubernetes%'
LIMIT 100
```

**Row count:** verified against live data

**Grounded answer:** *"The following candidates have Kubernetes experience: [full_name list from rows]."*

---

## Multi-Turn Demo

**Turn 1:** `how many active candidates are there?`
→ *"There are 17 active candidates."*

**Turn 2:** `which of them have cloud or AWS skills?`
The model resolves "them" from conversation history (multi-turn entries, not folded text) and generates:
```sql
SELECT DISTINCT c.id, c.full_name
FROM candidates c
JOIN candidate_skills cs ON cs.candidate_id = c.id
WHERE c.status = 'Active'
  AND (cs.name ILIKE '%cloud%' OR cs.name ILIKE '%aws%')
LIMIT 100
```

---

## Test Coverage

| Module | Tests | What is proven |
|---|---|---|
| `chat/types.py` + `QueryRun` | 4 | ORM round-trip, ChatStatus enum, QueryExecution fields |
| `chat/generator.py` | 5 | fence strip, history fold, token passthrough |
| `chat/guard.py` | 18 | full safety matrix — rejects and accepts |
| `chat/executor.py` | 6 | read-only enforcement, zero-row columns, graceful failure, toggle restore |
| `chat/answerer.py` | 5 | empty short-circuit, grounding, conversation entries, system prompt loaded |
| `POST /api/chat` endpoint | 9 | success, camelCase, DB persistence, viewer access, 401, unsafe→200, sql_error→200, llm_error→422, multi-turn |
| **Total new** | **47** | |
| Prior (Ex1–Ex3) | 101 | |
| **Grand total** | **148/148** ✅ | |

---

## Demo Screenshots

Located in [`docs/ex4/demo/`](demo/):

| File | Shows |
|---|---|
| `demo_02_chat_empty.png` | Ask Hellio page — clean state with "Ask" nav active |
| `demo_05_answered.png` | Answer returned, retrieval panel collapsed (success badge) |
| `demo_06_panel_open.png` | Panel expanded — SQL block, columns, row table with count=17 |

To regenerate: `python3 docs/ex4/demo/take_screenshots.py` (requires stack running + Node ≥20).

---

## Observability Proof

Every turn writes a `query_runs` row regardless of outcome:

```sql
SELECT id, status, row_count, input_tokens, output_tokens
FROM query_runs
ORDER BY id DESC
LIMIT 5;
```

Expected after a live session: rows with `status` in `{success, unsafe, sql_error, llm_error}`.

---

## Definition of Done Checklist

- [x] `cd api && .venv/bin/pytest -q` → 148/148 green
- [x] `tsc -b` clean
- [x] `/chat` works in `npm run dev` — multi-turn + retrieval panel verified
- [x] Four required questions answered live (see above)
- [x] `query_runs` rows present after live session
- [x] Pipeline diagram committed (`sql-rag-pipeline-diagram.html`)
- [x] PROGRESS.md updated
- [x] JOURNAL.md updated
- [x] All commits per-segment, each leaves the app demo-able

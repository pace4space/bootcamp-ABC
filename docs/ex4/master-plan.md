# Ex4 — SQL-RAG Chat (Master Plan)

## Context

Hellio HR has a stable UI contract (Ex1), a persistent FastAPI + Postgres backend (Ex2),
and an LLM ingestion pipeline that produces structured rows + summaries (Ex3). Ex4 adds the
first **interactive intelligence** feature: a chat window that answers natural-language
questions about candidates and positions by translating intent into SQL, retrieving rows,
and producing a **grounded** answer that references only retrieved data.

This is intentionally **SQL-first** (no embeddings, no agent, no MCP — those come in Ex5+).
The core is a classic **SQL-RAG loop**:

```
question (+ history)
        │
        ▼
  query/generator.py   → LLM (Nova) emits SQL          [system prompt = schema + rules + few-shot]
        │
        ▼
  query/guard.py       → SELECT-only safety validation  [reject DML/DDL/multi-statement; LIMIT cap]
        │
        ▼
  query/executor.py    → read-only execution           [SET TRANSACTION READ ONLY + statement_timeout]
        │
        ▼
  query/answerer.py    → LLM grounds answer in rows     [conversation entries = multi-turn history]
        │
        ▼
  ChatResponse(answer, sql, trace{rowCount, columns, rows}, model, runId)
  + query_runs row persisted (observability, Ex3-symmetric)
```

**Why a staged module, not a script:** identical rationale to Ex3's `pipeline/` — Ex6's HR
agent will call `run_chat_query()` the same way the endpoint does. Typed boundaries between
stages keep each independently testable.

### Locked decisions (confirmed with user)
1. **Hand-rolled SQL guard + read-only transaction** — no new dependency (no sqlglot).
2. **Persist a `query_runs` table** (Alembic `0003`) — symmetric with Ex3's `extraction_runs`;
   feeds the Ex4 reporting carry-forward note.
3. **Nova Lite only in the UI.** Bedrock billing is separate from Claude Pro; Claude-on-Bedrock
   is the same `converse()` API reachable via a one-line `modelId` swap behind a backend `model`
   param — built but not surfaced in the UI.

---

## Deliverable shape

The user wants the plan **divided into segmented `.md` files we can delegate to Sonnet**,
mirroring `docs/ex3/` (00-overview + numbered modules). So execution has two layers:

1. **Write `docs/ex4/*.md`** — 10 self-contained, test-first segment plans (the delegation units).
2. **Delegate each segment to Sonnet** for implementation, in dependency order, committing per segment.

### Segmented plans to author (`docs/ex4/`)

| File | Scope | Delegable unit |
|------|-------|----------------|
| `00-overview.md` | Purpose, SQL-RAG loop diagram, principles (grounding/safety/traceability/determinism), module map, carry-forward to Ex5 | — |
| `01-types-and-migration.md` | `query/types.py` dataclasses; `QueryRun` ORM model; Alembic `0003_query_runs.py` (scalar columns only — `columns_json` as JSON-encoded TEXT, **no ARRAY** → trivial SQLite tests) | Sonnet |
| `02-schema-context-and-prompts.md` | Curated Postgres schema description (table/column subset the LLM sees); versioned `prompts/sql-v1.txt` + `answer-v1.txt`; few-shot examples covering the 4 demo questions | Sonnet |
| `03-sql-generation.md` | `query/generator.py` → `generate_sql(question, history, client, model)`; reuse `BedrockClient.converse`; reuse `strip_fences`; model-routing param | Sonnet |
| `04-sql-safety.md` | `query/guard.py` → `validate_sql(sql)`; strip comments, single-statement, leading SELECT/WITH, keyword blocklist, LIMIT cap; full rejection test matrix | Sonnet |
| `05-query-execution.md` | `query/executor.py` → `execute_readonly(sql, db)`; Postgres `SET TRANSACTION READ ONLY` + `statement_timeout`, SQLite `PRAGMA query_only` for tests; bounded rows; graceful failure | Sonnet |
| `06-answer-synthesis.md` | `query/answerer.py` → `synthesize_answer(question, execution, history, client)`; grounded-only prompt; **conversation entries (multi-turn)**; no-rows handling; BedrockClient multi-turn extension | Sonnet |
| `07-endpoint-and-orchestration.md` | `query/__init__.py` → `run_chat_query()`; persist `QueryRun`; `routers/chat.py` `POST /api/chat`; `schemas.py` ChatRequest/ChatResponse; register in `main.py`; 422 + suggestion on failure | Sonnet |
| `08-chat-ui.md` | `lib/db.ts` `askChat()`; `pages/Chat.tsx` (messages, input, collapsible "What was retrieved" trace); route in `App.tsx`; nav link in `Layout.tsx`; multi-turn state | Sonnet |
| `09-testing-strategy.md` | Test layering mirroring `tests/pipeline/`; safety matrix; the 4 demo questions; Bedrock-mock + monkeypatch target; SQLite/Postgres ILIKE & read-only seam; manual live-Nova demo (Ex3 Step 9 style) | Sonnet |

---

## Architecture detail

### New backend module: `api/app/query/` (sibling to `pipeline/`)
```
api/app/query/
  types.py          ChatTurn, GeneratedSQL, QueryExecution, ChatResult, QueryRunRecord
  generator.py      generate_sql(question, history, client, model, prompt_version) -> GeneratedSQL
  guard.py          validate_sql(sql) -> SafeSQL   (raises UnsafeSQLError)
  executor.py       execute_readonly(sql, db) -> QueryExecution
  answerer.py       synthesize_answer(question, execution, history, client) -> (answer, tokens)
  __init__.py       run_chat_query(question, history, db, model) -> ChatResult  (orchestrator)
  prompts/
    sql-v1.txt      [SYSTEM] schema + rules + few-shot   [USER] {question}
    answer-v1.txt   [SYSTEM] grounding rules             [USER] {question}\n{rows_json}
```

### Reused utilities (do not reinvent)
- `BedrockClient` + `converse()` — `api/app/pipeline/llm.py:33`. Model-agnostic; Nova default.
  **Multi-turn extension:** add an *additive* `converse_messages(system, messages)` method (or
  optional `messages=` param) — keep the existing `converse(system, user)` signature untouched so
  Ex3 behavior is unchanged. The answerer uses conversation entries; the generator can fold a short
  history into its user message.
- `strip_fences` — currently `_strip_fences` at `api/app/pipeline/validator.py:32`. **Small refactor:**
  extract to `api/app/text_utils.py` (`strip_fences`), re-import in validator (re-export shim keeps
  Ex3 tests green), and import in `query/generator.py`. Nova non-deterministically fences output.
- `get_current_user` — `api/app/auth.py:48`. Chat is **read-only → any authenticated user (incl. viewer)**.
- Versioned-prompt loader pattern (`[SYSTEM]`/`[USER]` split) — `api/app/pipeline/llm.py:23`.
- Pydantic `_CONFIG` camelCase base — `api/app/schemas.py` (`alias_generator=to_camel`).
- Frontend seam `apiFetch(path, token, init)` — `src/lib/db.ts:9`.
- Test fixtures `client`, `auth_headers`, `viewer_headers`, `seeded_db`, ARRAY→JSON patch —
  `api/tests/conftest.py`. Seeded DB already has Active+Archived candidates, Open+Closed positions,
  skills, requirements, applications — sufficient for executor + endpoint tests.

### Critical files to create / modify
**Create:** `docs/ex4/00..09*.md`; `api/app/query/{types,generator,guard,executor,answerer,__init__}.py`;
`api/app/query/prompts/{sql-v1,answer-v1}.txt`; `api/app/routers/chat.py`; `api/app/text_utils.py`;
`api/alembic/versions/0003_query_runs.py`; `api/tests/query/{conftest,test_guard,test_generator,test_executor,test_answerer,test_chat_endpoint}.py`;
`src/pages/Chat.tsx`.
**Modify:** `api/app/models.py` (+`QueryRun`); `api/app/schemas.py` (+ChatRequest/ChatTurn/ChatResponse/ChatTrace);
`api/app/main.py` (register `chat.router`); `api/app/pipeline/llm.py` (additive multi-turn method);
`api/app/pipeline/validator.py` (import from `text_utils`); `src/lib/db.ts` (+`askChat`);
`src/App.tsx` (+`/chat` route); `src/components/Layout.tsx` (+nav link).

### `query_runs` table (Alembic 0003) — SQLite-friendly, no ARRAY
`id, question TEXT, generated_sql TEXT, prompt_version TEXT, prompt_text TEXT, model_id TEXT,
row_count INT, columns_json TEXT, status TEXT CHECK(status IN ('success','unsafe','sql_error','llm_error')),
error TEXT NULL, input_tokens INT, output_tokens INT, latency_ms INT, created_at TIMESTAMPTZ`.
Supply explicit `datetime.now(UTC)` at write time (SQLite can't read `server_default='now()'` — known
project pattern). Persist via `flush()`; the endpoint commits once (mirrors Ex3 logger/persister).

### Safety model (defense-in-depth, hand-rolled)
1. **Prompt:** "emit a single read-only SELECT; never write."
2. **Guard (`validate_sql`):** strip `--`/`/* */` comments; reject if >1 statement (stray `;`);
   require first keyword ∈ {`SELECT`,`WITH`}; blocklist `INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|
   CREATE|GRANT|REVOKE|ATTACH|PRAGMA|COPY|;`; append `LIMIT 100` if absent. Returns `SafeSQL` or raises.
3. **Execution:** Postgres `SET TRANSACTION READ ONLY` + `SET LOCAL statement_timeout='5s'` inside the
   request transaction; the DB itself refuses any write that slips past the guard. (SQLite tests use
   `PRAGMA query_only=ON`.) A dedicated read-only DB role is noted as a documented future hardening.

### Resilience (NFR)
- LLM-gen failure → 422 `{error, suggestion}` ("try rephrasing / be more specific").
- Guard rejection → 422 with the offending SQL echoed and reason.
- SQL execution error → caught, persisted as `sql_error`, returned as a clean message (no 500).

---

## Verification

**Per-segment (automated, Bedrock mocked):**
- `cd api && .venv/bin/pytest -q` — all existing tests stay green (101) + new `tests/query/` green.
- Safety matrix: `test_guard` asserts rejection of `DROP TABLE`, `; DELETE`, `UPDATE`, comment-hidden
  DML, multi-statement; acceptance of `SELECT`/`WITH`; LIMIT cap appended.
- `test_executor` asserts read-only enforcement (a write raises) + correct columns/row_count on `seeded_db`.
- `test_chat_endpoint` mocks `app.query.BedrockClient` (monkeypatch the name imported into `app.query`,
  not the definition site — known project pattern), feeds a known SQL, asserts grounded answer + trace
  + `query_runs` row + viewer can call it (read-only).

**End-to-end (manual, live Nova — Ex3 Step 9 style):** with Postgres up (`docker compose up`) and
real Bedrock creds, POST each of the four required questions and confirm SQL + grounded answer + trace:
1. "list open position counts by department" 2. "which positions do not have any candidate"
3. "which positions have more than X candidates" 4. "list all candidates with kubernetes experience".
Record responses in `docs/ex4/submission-ex4.md`.

**UI:** `npm run dev` → `/chat` → multi-turn Q&A; each answer shows a collapsible
"What was retrieved" panel (SQL + rowCount + columns). `tsc -b` + `npm run build` clean.

---

## Build handoff (confirmed with user): clean PLAN/BUILD split

```
Opus (THIS session):  branch ex4  ->  write docs/ex4/*.md + master-plan copy  ->  commit  ->  STOP
You:                  open a NEW session on Sonnet, pointed at docs/ex4
Sonnet (BUILD):       read docs/ex4/00..09  ->  implement + test each segment  ->  commit per segment
```

This is the user's stated goal — **delegate to Sonnet via segmented plans** — so the `docs/ex4/*.md`
files ARE the handoff contract. They must be self-contained: each segment states the exact public
signatures, the reused utilities with `file:line` pointers, the test cases (names + assertions), and
its dependency on prior segments. A fresh Sonnet session must be able to implement test-first with no
further Opus input. Opus cost = planning only.

### This session's execution sequence (Opus)
1. `git checkout -b ex4` off `master`.
2. Author `docs/ex4/00..09*.md` (route the format-heavy prose to Haiku per the model-routing skill;
   keep the design decisions/signatures precise).
3. Copy this master plan to `docs/ex4/master-plan.md` (version-controlled reference, as requested).
4. `git add docs/ex4 && git commit` (segment plans only — **no source code written this session**).
5. Stop. Report the branch + files + the exact prompt to start the Sonnet BUILD session.

## Workflow notes
- **Commit every working step** (per CLAUDE.md); each BUILD commit leaves the app demo-able.
- **JOURNAL.md** entry per commit; **PROGRESS.md** Ex4 section — written during BUILD by Sonnet.
- **Model routing:** this planning + segment authoring = Opus/Haiku; module implementation +
  test design = Sonnet (fresh session). Honors Opus-plans / Sonnet-builds.
- **post-commit hook** logs to `.skilllog`; run `/memory-synthesize` at the 5-commit cadence (BUILD).

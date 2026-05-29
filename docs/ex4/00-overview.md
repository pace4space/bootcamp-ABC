# Ex4 — Exercise Overview & Architecture (SQL-RAG Chat)

> **For the Sonnet BUILD session.** These 10 segment files (`00`–`09`) are the handoff
> contract. Each is self-contained: exact signatures, reused utilities with `file:line`
> pointers, test names + assertions, and its dependency on prior segments. Implement
> **test-first**, in numeric order. Commit per segment. Do not start a segment before its
> stated dependencies are green.

## Purpose

Ex4 adds the first **interactive intelligence** feature to Hellio HR: a chat window that
answers natural-language questions about candidates and positions. It does this with a
**SQL-RAG loop** — translate intent → SQL, retrieve rows, ground an answer in those rows.

Intentionally **SQL-first**. No embeddings, no semantic search, no agent, no MCP — those are
Ex5+. No writes to the DB: every generated query is **read-only**.

## The SQL-RAG loop

```
question (+ optional chat history)
        │
        ▼
  query/generator.py   → LLM (Nova Lite) emits ONE SQL SELECT   [system prompt = schema + rules + few-shot]
        │
        ▼
  query/guard.py       → SELECT-only safety validation          [reject DML/DDL/multi-statement; LIMIT cap]
        │
        ▼
  query/executor.py    → read-only execution                    [SET TRANSACTION READ ONLY + statement_timeout]
        │
        ▼
  query/answerer.py    → LLM grounds an answer in the rows       [conversation entries = multi-turn history]
        │
        ▼
  ChatResponse(answer, sql, trace{rowCount, columns, rows}, model, runId)
  + a query_runs row persisted (observability, symmetric with Ex3's extraction_runs)
```

## Three principles (the lessons of this exercise)

1. **Grounding over invention.** The answerer may reference ONLY the rows returned by the
   executor. No invented candidates, positions, counts, or names. If zero rows: say so plainly.
2. **Safety is layered, not trusted to the prompt.** The LLM is asked for a SELECT, but the
   guard *enforces* SELECT-only deterministically, and the DB executes in a read-only
   transaction. Defense in depth — three independent layers, any one of which blocks a write.
3. **Traceability by default.** Every chat turn returns the executed SQL, the row count, and
   the columns; and persists a `query_runs` row (question, SQL, prompt, model, tokens, status).
   A retrieval you cannot inspect is not debuggable.

A fourth, quieter principle: **predictability over cleverness** (NFR). Prefer a boring,
explainable SELECT and a literal grounded answer over a clever query that's hard to audit.

## What we have entering Ex4

- Running FastAPI + Postgres backend (Ex2) with a populated, normalized schema.
- Document-derived candidate/position rows + summaries (Ex3).
- `BedrockClient.converse()` — model-agnostic Bedrock wrapper (`api/app/pipeline/llm.py:33`).
- Versioned-prompt pattern (`[SYSTEM]`/`[USER]` split) — `api/app/pipeline/llm.py:23`.
- `_strip_fences()` — LLM markdown-fence stripper (`api/app/pipeline/validator.py:32`).
- A seeded SQLite test DB with Active+Archived candidates, Open+Closed positions, skills,
  requirements, applications (`api/tests/conftest.py`) — enough for executor + endpoint tests.

## What we produce

- A `query/` module with 5 stages + an orchestrator, each independently testable
  (sibling to Ex3's `pipeline/`).
- One new endpoint: `POST /api/chat` (read-only → any authenticated user, incl. viewer).
- One new DB table: `query_runs` (Alembic `0003`).
- Versioned prompts: `query/prompts/sql-v1.txt`, `answer-v1.txt`.
- A `Chat.tsx` page with multi-turn Q&A and a per-answer "What was retrieved" trace panel.
- Full automated test coverage with Bedrock mocked; a manual live-Nova demo for the 4 questions.

## Module learning map

| Segment | Module | Core lesson |
|---------|--------|-------------|
| 01 | `types.py` + `0003` migration | Typed stage boundaries; an observability table that's SQLite-portable (no ARRAY) |
| 02 | schema context + prompts | The schema in the prompt is a *curated contract*, not a `pg_dump`; few-shot teaches the shape |
| 03 | `generator.py` | The LLM is an injected dependency; prompts are versioned; output is untrusted text |
| 04 | `guard.py` | LLM SQL is untrusted input. Enforce SELECT-only deterministically, never via prompt alone |
| 05 | `executor.py` | Read-only is a transaction property, not a hope. Bound the result. Failure ≠ crash |
| 06 | `answerer.py` | Grounding = the model may only cite retrieved rows. Multi-turn = conversation entries |
| 07 | `__init__.py` + `routers/chat.py` | HTTP is a translation layer: domain outcomes → status codes + a trace |
| 08 | `Chat.tsx` + `lib/db.ts` | The UI shows *what was retrieved*, making the RAG loop legible to a human |
| 09 | testing strategy | Mock Bedrock everywhere automated; verify the 4 real questions live (Ex3 Step 9 style) |

## Locked decisions (do not relitigate)

1. **Hand-rolled SQL guard + read-only transaction.** No new dependency (no `sqlglot`).
2. **Persist a `query_runs` table** (Alembic `0003`) — symmetric with Ex3's `extraction_runs`.
3. **Nova Lite only in the UI.** Claude-on-Bedrock is the same `converse()` API, reachable via a
   one-line `modelId` swap behind a backend `model` param; built, not surfaced in the UI.
   (Bedrock billing is separate from Claude Pro; Claude-via-Bedrock is incremental AWS cost.)

## Carry-forward

- **Ex5 (embeddings):** the `query_runs` log + this chat UI become the shell that semantic
  retrieval slots into — the loop stays; only the retrieval step gains a vector path.
- **Ex6 (agent):** `run_chat_query()` is a callable function; the HR agent invokes it like the
  endpoint does — same as Ex3's `run_cv_pipeline()`.
- **Reporting:** `query_runs` token/latency data mirrors `extraction_runs`, enabling a cost
  dashboard later.

## Conventions inherited from Ex2/Ex3 (apply throughout)

- Async SQLAlchemy 2.x; `AsyncSession` via `Depends(get_db)` (`api/app/db.py:64`).
- Pydantic camelCase via `_CONFIG` (`alias_generator=to_camel`) — `api/app/schemas.py`.
- Persist via `flush()` inside the request; the **endpoint** calls `db.commit()` once.
- SQLite tests: supply explicit `datetime.now(timezone.utc)` at write time — never rely on
  `server_default="now()"` (it's Postgres syntax SQLite can't read).
- Monkeypatch the name in the namespace that imported it (`app.query.BedrockClient`), not the
  definition site (`app.query.generator.BedrockClient`). See segment 09.

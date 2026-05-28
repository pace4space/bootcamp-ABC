# Ex3 — Module 6: Observability & Logging

## Problem

We need to answer these questions after the fact:
1. What text did we extract from CV X?
2. Which model was used, and what did it cost?
3. Why did ingestion fail for CV Y?
4. What was the exact prompt sent to the LLM?

None of these are answerable from application logs alone. They require structured DB records.

## Two Tables, Two Purposes

### `raw_documents` — "What did we receive?"

Written immediately after parsing, **before** any LLM call. Even if the LLM times out or
validation fails, the raw text is preserved. This table is also the input for Ex5
(embeddings): no re-parsing needed.

```sql
CREATE TABLE raw_documents (
    id              SERIAL PRIMARY KEY,
    filename        TEXT NOT NULL,
    format          TEXT NOT NULL,         -- 'pdf' | 'docx' | 'txt'
    document_kind   TEXT NOT NULL,         -- 'cv' | 'position'
    raw_text        TEXT NOT NULL,
    char_count      INTEGER NOT NULL,
    uploaded_at     TIMESTAMPTZ DEFAULT now()
);
```

### `extraction_runs` — "What did the pipeline do with it?"

Written at the end of every run — success, partial, or failure. Includes:
- Full rendered prompt (reproducible)
- Verbatim LLM output (inspectable)
- Status, errors, warnings
- Token counts (cost observable)
- Latency in ms

```sql
CREATE TABLE extraction_runs (
    id                  SERIAL PRIMARY KEY,
    raw_document_id     INTEGER NOT NULL REFERENCES raw_documents(id),
    model_id            TEXT NOT NULL,
    prompt_version      TEXT NOT NULL,
    prompt_text         TEXT NOT NULL,
    raw_llm_output      TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('success', 'partial', 'failed')),
    entity_id           TEXT,              -- NULL on failure
    errors              TEXT[] NOT NULL DEFAULT '{}',
    warnings            TEXT[] NOT NULL DEFAULT '{}',
    input_tokens        INTEGER NOT NULL DEFAULT 0,
    output_tokens       INTEGER NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT now()
);
```

## Unconditional Logging

The raw document is logged **before** the LLM call. The extraction run is logged **after**
every outcome — including failures. There is no code path that returns without writing both.

This is a deliberate design choice against "only log on success." Failed runs are the most
valuable log entries: they tell you what the pipeline couldn't handle. Suppressing them
makes the pipeline opaque to debugging.

## Cost Queries

```sql
-- Total cost by model, all time
SELECT model_id, COUNT(*) runs,
       SUM(input_tokens) total_input,
       SUM(output_tokens) total_output,
       ROUND(SUM(input_tokens * 0.00006 + output_tokens * 0.00024) / 1000, 4) est_usd
FROM extraction_runs
GROUP BY model_id;

-- Failed runs this week
SELECT id, entity_id, status, errors, created_at
FROM extraction_runs
WHERE status = 'failed'
  AND created_at > now() - interval '7 days'
ORDER BY created_at DESC;

-- Replay a specific run (full prompt + raw response)
SELECT prompt_text, raw_llm_output
FROM extraction_runs
WHERE id = 42;

-- Candidates with extraction warnings (PARTIAL status)
SELECT entity_id, warnings, created_at
FROM extraction_runs
WHERE status = 'partial'
ORDER BY created_at DESC;
```

## Public Interface

```python
# api/app/pipeline/logger.py

async def log_raw_document(doc: RawDocument, db: AsyncSession) -> int:
    """Insert into raw_documents. Returns row id."""

async def log_extraction_run(
    raw_doc_id: int,
    llm_response: LLMResponse,
    result: ExtractionResult,
    db: AsyncSession,
) -> int:
    """Insert into extraction_runs. Returns row id."""
```

## SQLite Test Note

`errors` and `warnings` use `ARRAY(Text)` in Postgres. The test suite uses SQLite (in-memory).
Apply the same `conftest.py` patch used for `CandidateExperience.highlights`:

```python
# api/tests/conftest.py — add alongside existing highlights patch
from sqlalchemy import event
@event.listens_for(ExtractionRun.__table__, "before_create")
def _patch_extraction_run_arrays(target, connection, **kw):
    if connection.dialect.name == "sqlite":
        target.c.errors.type = JSON()
        target.c.warnings.type = JSON()
```

## Interview Talking Point

> "Why not just use Python's `logging` module for pipeline observability?"

Application logs are ephemeral, hard to query, and don't survive process restarts or
container redeployments. DB records are queryable, persistent, and joinable. We want to
run `SELECT SUM(input_tokens) FROM extraction_runs` six months from now and get the answer.
That requires structured storage, not log files.

# Ex4 — Segment 01: Types & Migration

**Depends on:** nothing (start here). **Blocks:** all other segments import from `query/types.py`;
07 persists `QueryRun`; 09 patches nothing new (no ARRAY columns).

## Goal

1. Define the typed boundaries between the SQL-RAG stages (`api/app/query/types.py`).
2. Add a `QueryRun` ORM model (`api/app/models.py`) + Alembic `0003` migration for `query_runs`.

Mirror the Ex3 style: `api/app/pipeline/types.py` for dataclasses, `0002_pipeline_tables.py`
for the migration. **Critical difference: `query_runs` uses NO `ARRAY` columns** — store the
column-name list as a JSON-encoded TEXT string (`columns_json`). This keeps SQLite tests trivial
(no `__table__.c.x.type = JSON()` patch needed, unlike `extraction_runs`).

## File: `api/app/query/types.py`

```python
"""Type contracts for the SQL-RAG query module.

Every stage communicates only through these types. No stage imports from
another stage except via this module (same discipline as pipeline/types.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ChatStatus(str, Enum):
    SUCCESS = "success"        # SQL generated, passed guard, executed, answer grounded
    UNSAFE = "unsafe"          # guard rejected the generated SQL
    SQL_ERROR = "sql_error"    # SQL executed but the DB raised (syntax, bad column, timeout)
    LLM_ERROR = "llm_error"    # generation or answer synthesis call failed


@dataclass
class ChatTurn:
    """One prior turn of the conversation. role ∈ {'user','assistant'}."""
    role: str
    content: str


@dataclass
class GeneratedSQL:
    """Output of generator.py — the raw model proposal, pre-guard."""
    sql: str                  # stripped of fences; NOT yet validated
    model_id: str
    prompt_version: str
    prompt_text: str          # full rendered prompt (system + user) — stored for replay
    input_tokens: int
    output_tokens: int
    latency_ms: int


@dataclass
class QueryExecution:
    """Output of executor.py. ok=False carries the DB error message (no exception leaks)."""
    ok: bool
    columns: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)  # JSON-safe scalars
    row_count: int = 0
    error: Optional[str] = None


@dataclass
class ChatResult:
    """The orchestrator's final return value → mapped to ChatResponse in the router."""
    status: ChatStatus
    answer: str
    sql: str                  # the SQL we attempted (post-guard if it got that far, else raw)
    execution: QueryExecution
    model_id: str
    run_id: int = -1          # FK to query_runs; -1 if not logged yet
    input_tokens: int = 0
    output_tokens: int = 0
    error: Optional[str] = None       # human-facing error, when status != SUCCESS
    suggestion: Optional[str] = None  # resilience: "try rephrasing…"
```

**Notes for the implementer**
- `rows` must hold JSON-safe scalars (str/int/float/bool/None). The executor (05) is responsible
  for coercion; types.py just declares the shape.
- `GeneratedSQL.sql` is fence-stripped but unvalidated — the guard (04) is the only thing that
  blesses SQL as safe.

## File: `api/app/models.py` — append `QueryRun`

Add at the end of the file (after `ExtractionRun`). **No `ARRAY` columns.**

```python
# ---------------------------------------------------------------------------
# query_runs  (Ex4 SQL-RAG observability — append-only)
# Mirrors extraction_runs, but SQLite-portable: columns list is JSON-in-TEXT.
# ---------------------------------------------------------------------------

class QueryRun(Base):
    __tablename__ = "query_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # null if LLM failed
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    columns_json: Mapped[str] = mapped_column(Text, nullable=False, server_default="[]")  # JSON list of col names
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'unsafe', 'sql_error', 'llm_error')",
            name="query_runs_status_check",
        ),
    )
```

(`Integer`, `Text`, `TIMESTAMP`, `CheckConstraint`, `Mapped`, `mapped_column`, `datetime`,
`Optional` are all already imported at the top of `models.py` — verify, add none that exist.)

## File: `api/alembic/versions/0003_query_runs.py`

Copy the shape of `0002_pipeline_tables.py`. **`down_revision = "0002"`.** No `postgresql.ARRAY`.

```python
"""Ex4 SQL-RAG observability table: query_runs.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-29

Append-only log of every chat turn: question, generated SQL, prompt, model, tokens, status.
No FK to candidates/positions — a failed/unsafe query that produced no rows still needs a row.
Deliberately no ARRAY columns (columns list is JSON-in-TEXT) so the same DDL runs on SQLite.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "query_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("columns_json", sa.Text(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="query_runs_pkey"),
        sa.CheckConstraint(
            "status IN ('success', 'unsafe', 'sql_error', 'llm_error')",
            name="query_runs_status_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("query_runs")
```

## Tests (`api/tests/query/test_types_models.py`) — write first, watch them fail, then implement

| Test | Assertion |
|------|-----------|
| `test_query_run_roundtrip` | Insert a `QueryRun` with explicit `created_at=datetime.now(timezone.utc)` into `seeded_db`; read it back; fields match. Proves the model + table create_all on SQLite **without any ARRAY patch**. |
| `test_query_run_status_check` | (Postgres-only behavior; on SQLite the CHECK is created but may not enforce — assert the constraint exists in `__table_args__`, or skip enforcement assertion on SQLite.) |
| `test_chatresult_defaults` | `ChatResult(status=ChatStatus.SUCCESS, answer="x", sql="SELECT 1", execution=QueryExecution(ok=True), model_id="m")` → `run_id == -1`, `input_tokens == 0`. |

**conftest note:** add `QueryRun` to the imports in `api/tests/conftest.py` (the `from app.models import (...)` block) so `Base.metadata.create_all` builds the table. No `.type = JSON()` patch needed — that's the whole point of `columns_json`.

## Verification
- `cd api && .venv/bin/pytest tests/query/test_types_models.py -q` → green.
- `cd api && .venv/bin/pytest -q` → existing 101 still green (you only added a table + a model).
- Migration sanity: `alembic upgrade head` then `alembic downgrade -1` round-trips against Postgres
  (verify during the segment 07 integration / live demo, not required for unit green).

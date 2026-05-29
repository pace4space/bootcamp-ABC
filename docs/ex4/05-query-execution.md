# Ex4 — Segment 05: Query Execution (read-only)

**Depends on:** 01 (types). **Blocks:** 07 (orchestrator calls `execute_readonly`).

## Goal

`query/executor.py` runs guard-approved SQL **read-only**, captures columns + rows + row_count,
and **never raises** — a DB error becomes `QueryExecution(ok=False, error=...)`. Read-only is a
*transaction property*, not a hope: even if a write slipped past the guard (04), the DB rejects it.

## The Postgres/SQLite read-only seam (documented design decision)

In production the DB is **Postgres**: run the untrusted SQL on its **own isolated connection** in a
`READ ONLY` transaction with a `statement_timeout` — fully sandboxed from the request/logging
session. In tests the DB is **in-memory SQLite**, where a second connection is a *different* empty
database, so we instead reuse the request connection and sandbox the read with
`PRAGMA query_only = ON/OFF`. One small dialect branch, each side correct for its environment — the
same spirit as Ex3's documented ARRAY→JSON and `server_default` seams.

```python
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .types import QueryExecution

_MAX_ROWS = 200          # hard cap beyond the guard's LIMIT 100 — defense in depth
_TIMEOUT_MS = 5000


def _jsonable(v: Any) -> Any:
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v   # str/int/float/bool/None pass through


async def execute_readonly(sql: str, db: AsyncSession) -> QueryExecution:
    bind = db.get_bind()
    dialect = bind.dialect.name
    try:
        if dialect == "sqlite":
            # tests: reuse the session connection; PRAGMA sandboxes the read, then restore
            conn = await db.connection()
            await conn.execute(text("PRAGMA query_only = ON"))
            try:
                result = await conn.execute(text(sql))
                mappings = result.mappings().fetchmany(_MAX_ROWS)
                columns = list(result.keys())
            finally:
                await conn.execute(text("PRAGMA query_only = OFF"))
        else:
            # prod (postgres): isolated read-only connection, never committed
            async with bind.connect() as conn:
                await conn.execute(text("SET TRANSACTION READ ONLY"))
                await conn.execute(text(f"SET statement_timeout = {_TIMEOUT_MS}"))
                result = await conn.execute(text(sql))
                mappings = result.mappings().fetchmany(_MAX_ROWS)
                columns = list(result.keys())

        rows = [{k: _jsonable(v) for k, v in m.items()} for m in mappings]
        return QueryExecution(ok=True, columns=columns, rows=rows, row_count=len(rows))
    except Exception as e:  # noqa: BLE001 — any DB error is a graceful domain outcome here
        return QueryExecution(ok=False, error=str(e))
```

## Design notes

- **`ok=False`, not an exception.** Robustness NFR: a bad column name, a syntax slip, or a timeout
  returns a clean `QueryExecution` the orchestrator logs as `sql_error` and the endpoint surfaces as
  a 422 with a suggestion — never a 500.
- **`_MAX_ROWS` cap** is independent of the guard's `LIMIT 100`: if a future prompt change drops the
  LIMIT, the executor still bounds memory and response size.
- **`fetchmany(_MAX_ROWS)`** + `result.keys()` give us columns even for zero-row results (important
  for the trace and for the answerer's "no rows" path).
- **JSON-safe rows** (`_jsonable`): datetimes/Decimals are coerced so `json.dumps` in the answerer
  (06) and the `ChatResponse` serializer (07) never choke.
- **Why the sqlite branch reuses `db.connection()`:** in-memory SQLite is per-connection; a fresh
  `bind.connect()` would see an empty schema. `PRAGMA query_only` gives a genuine read-only guarantee
  on that one connection, and toggling it OFF afterward lets segment 07 insert the `query_runs` row on
  the same session. (Postgres has no such limitation — it gets the cleaner isolated connection.)

## Tests (`api/tests/query/test_executor.py`) — write first

Use the seeded `seeded_db` session from `api/tests/conftest.py` (Active+Archived candidates,
Open+Closed positions, applications). Open a session and pass it to `execute_readonly`.

| Test | Assertion |
|------|-----------|
| `test_select_returns_rows_and_columns` | `SELECT id, full_name FROM candidates WHERE status='Active'` → `ok` True, `columns == ['id','full_name']`, `row_count >= 2`, rows are dicts. |
| `test_anti_join_open_positions_without_candidates` | the LEFT JOIN…IS NULL query → `ok` True; returns the open position(s) with no application (e.g. `pos_t02` has applications, so craft seeded expectation accordingly — assert it runs and row_count is an int). |
| `test_zero_rows_has_columns` | `SELECT id FROM candidates WHERE id='nope'` → `ok` True, `row_count == 0`, `columns == ['id']`. |
| `test_bad_column_is_graceful` | `SELECT nonexistent FROM candidates` → `ok` False, `error` non-empty, no exception escapes. |
| `test_readonly_blocks_write` | run `UPDATE candidates SET status='x'` (bypassing the guard, calling executor directly) → on sqlite `PRAGMA query_only` makes this `ok` False with an error mentioning read-only / not authorized. Proves the executor layer refuses writes even if the guard were bypassed. |
| `test_datetime_is_jsonable` | a query returning `created_at` from applications → the value is a `str` (isoformat), so `json.dumps(rows)` succeeds. |

(After `test_readonly_blocks_write`, the `finally` restores `query_only = OFF`; assert a subsequent
read on the same session still works, proving the toggle doesn't poison the connection.)

## Verification
- `cd api && .venv/bin/pytest tests/query/test_executor.py -q` → green.
- Full suite green: `.venv/bin/pytest -q`.
- Postgres read-only path is verified in the live demo (09), not in unit tests (no PG in CI).

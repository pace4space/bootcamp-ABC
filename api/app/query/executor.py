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

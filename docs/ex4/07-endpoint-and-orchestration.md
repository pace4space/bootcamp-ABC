# Ex4 — Segment 07: Orchestration & Endpoint

**Depends on:** 01–06 (all stages). **Blocks:** 08 (UI calls the endpoint), 09 (endpoint test).

## Goal

Wire the five stages into `run_chat_query()` (the callable Ex6's agent will reuse), persist a
`query_runs` row for every turn, and expose `POST /api/chat`. HTTP is a translation layer:
domain outcome → status code + a trace.

## File: `api/app/query/__init__.py` — the orchestrator

```python
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QueryRun
from app.pipeline.llm import BedrockClient, BedrockError

from .answerer import synthesize_answer
from .executor import execute_readonly
from .generator import generate_sql
from .guard import UnsafeSQLError, validate_sql
from .types import ChatResult, ChatStatus, ChatTurn, GeneratedSQL, QueryExecution

_RETRY_SUGGESTION = (
    "Try rephrasing your question, or be more specific about candidates or positions."
)


async def run_chat_query(
    question: str,
    history: list[ChatTurn] | None,
    db: AsyncSession,
    model: str | None = None,
    bedrock_client: BedrockClient | None = None,
) -> ChatResult:
    history = history or []

    # --- Stage 1: generate SQL -------------------------------------------------
    try:
        gen: GeneratedSQL = await generate_sql(
            question, history, bedrock_client=bedrock_client, model=model
        )
    except BedrockError as e:
        return await _finish(
            db, question, None, gen=None, status=ChatStatus.LLM_ERROR,
            answer="", execution=QueryExecution(ok=False, error=str(e)),
            model_id=model or "", error=f"SQL generation failed: {e}",
            suggestion=_RETRY_SUGGESTION, in_tok=0, out_tok=0,
        )

    # --- Stage 2: guard --------------------------------------------------------
    try:
        safe_sql = validate_sql(gen.sql)
    except UnsafeSQLError as e:
        return await _finish(
            db, question, gen.sql, gen=gen, status=ChatStatus.UNSAFE,
            answer="", execution=QueryExecution(ok=False, error=e.reason),
            model_id=gen.model_id, error=f"Generated query was rejected: {e.reason}",
            suggestion=_RETRY_SUGGESTION, in_tok=gen.input_tokens, out_tok=gen.output_tokens,
        )

    # --- Stage 3: execute (read-only) -----------------------------------------
    execution = await execute_readonly(safe_sql, db)
    if not execution.ok:
        return await _finish(
            db, question, safe_sql, gen=gen, status=ChatStatus.SQL_ERROR,
            answer="", execution=execution, model_id=gen.model_id,
            error=f"The query could not be executed: {execution.error}",
            suggestion=_RETRY_SUGGESTION, in_tok=gen.input_tokens, out_tok=gen.output_tokens,
        )

    # --- Stage 4: synthesize grounded answer ----------------------------------
    try:
        answer, a_in, a_out = await synthesize_answer(
            question, execution, history, bedrock_client=bedrock_client
        )
    except BedrockError as e:
        return await _finish(
            db, question, safe_sql, gen=gen, status=ChatStatus.LLM_ERROR,
            answer="", execution=execution, model_id=gen.model_id,
            error=f"Answer synthesis failed: {e}", suggestion=_RETRY_SUGGESTION,
            in_tok=gen.input_tokens, out_tok=gen.output_tokens,
        )

    return await _finish(
        db, question, safe_sql, gen=gen, status=ChatStatus.SUCCESS,
        answer=answer, execution=execution, model_id=gen.model_id, error=None,
        suggestion=None, in_tok=gen.input_tokens + a_in, out_tok=gen.output_tokens + a_out,
    )


async def _finish(db, question, sql, *, gen, status, answer, execution,
                  model_id, error, suggestion, in_tok, out_tok) -> ChatResult:
    """Persist a query_runs row (flush only — endpoint commits) and build ChatResult."""
    run = QueryRun(
        question=question,
        generated_sql=sql,
        prompt_version=gen.prompt_version if gen else "sql-v1",
        prompt_text=gen.prompt_text if gen else "",
        model_id=model_id or (gen.model_id if gen else ""),
        row_count=execution.row_count,
        columns_json=json.dumps(execution.columns),
        status=status.value,
        error=error,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=gen.latency_ms if gen else 0,
        created_at=datetime.now(timezone.utc),   # never rely on server_default for SQLite
    )
    db.add(run)
    await db.flush()   # assigns run.id; endpoint commits once
    return ChatResult(
        status=status, answer=answer, sql=sql or "", execution=execution,
        model_id=run.model_id, run_id=run.id, input_tokens=in_tok, output_tokens=out_tok,
        error=error, suggestion=suggestion,
    )
```

**Notes:** `flush()` not `commit()` (Ex3 logger/persister pattern — the endpoint owns the commit).
Explicit `created_at` (SQLite can't read `server_default="now()"`). Every path writes exactly one
`query_runs` row — observability is unconditional (success, unsafe, sql_error, llm_error).

## File: `api/app/schemas.py` — append (camelCase via the existing `_CONFIG`)

```python
class ChatTurn(BaseModel):
    model_config = _CONFIG
    role: str          # 'user' | 'assistant'
    content: str

class ChatRequest(BaseModel):
    model_config = _CONFIG
    question: str
    history: list[ChatTurn] = []
    model: Optional[str] = None      # None → Nova default; not surfaced in UI

class ChatTrace(BaseModel):
    model_config = _CONFIG
    row_count: int
    columns: list[str]
    rows: list[dict] = []            # capped; what was retrieved
    prompt_version: str = "sql-v1"

class ChatResponse(BaseModel):
    model_config = _CONFIG
    answer: str
    sql: str
    status: str                      # ChatStatus value
    model: str
    run_id: int
    trace: ChatTrace
    error: Optional[str] = None
    suggestion: Optional[str] = None
```

## File: `api/app/routers/chat.py`

```python
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status as http
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user           # read-only → ANY authenticated user (incl. viewer)
from app.db import get_db
from app.models import User
from app.query import run_chat_query
from app.query.types import ChatStatus, ChatTurn
from app.schemas import ChatRequest, ChatResponse, ChatTrace

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> ChatResponse:
    history = [ChatTurn(role=t.role, content=t.content) for t in body.history]
    result = await run_chat_query(body.question, history, db, model=body.model)
    await db.commit()   # commit the query_runs row regardless of outcome

    # Hard LLM failure → 422 (loop could not run). Unsafe / sql_error → 200 with a trace, so the
    # chat UI can show what happened (the diagnostic IS the value). See design note below.
    if result.status == ChatStatus.LLM_ERROR:
        raise HTTPException(
            status_code=http.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"error": result.error, "suggestion": result.suggestion},
        )

    return ChatResponse(
        answer=result.answer,
        sql=result.sql,
        status=result.status.value,
        model=result.model_id,
        run_id=result.run_id,
        trace=ChatTrace(
            row_count=result.execution.row_count,
            columns=result.execution.columns,
            rows=result.execution.rows,
        ),
        error=result.error,
        suggestion=result.suggestion,
    )
```

**Design note (status-code policy — minor, explicit refinement of the master plan):** the master
plan said "guard rejection → 422." For a *chat* surface, returning 200 with `status='unsafe'` +
`error` + the offending `sql` in the trace is better UX — the conversation continues and the
"what was retrieved" panel explains the rejection. So only `LLM_ERROR` (the loop couldn't start)
is a 422; `UNSAFE` and `SQL_ERROR` return 200 with diagnostic fields. This keeps the frontend (08)
simple: it branches on `status`, not on HTTP codes. If strict 422-on-rejection is preferred, raise
for `UNSAFE`/`SQL_ERROR` too — the `ChatResult` carries everything needed either way.

## File: `api/app/main.py` — register the router

```python
from app.routers import applications, auth, candidates, chat, ingest, positions
...
app.include_router(chat.router, prefix="/api")
```

## Verification
- `cd api && .venv/bin/pytest tests/query/test_chat_endpoint.py -q` → green (see segment 09).
- `.venv/bin/pytest -q` → full suite green.
- Schema sanity: `ChatResponse` serializes camelCase (`rowCount`, `runId`) — verified in 09.

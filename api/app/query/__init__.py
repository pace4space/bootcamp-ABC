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

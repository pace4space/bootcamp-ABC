"""Segment 01 tests — types dataclasses + QueryRun ORM model."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models import QueryRun
from app.query.types import ChatResult, ChatStatus, QueryExecution


@pytest.mark.asyncio
async def test_query_run_roundtrip(seeded_db):
    async with seeded_db() as db:
        run = QueryRun(
            question="list all candidates",
            generated_sql="SELECT id FROM candidates",
            prompt_version="sql-v1",
            prompt_text="[SYSTEM]\ntest\n\n[USER]\nlist all candidates",
            model_id="amazon.nova-lite-v1:0",
            row_count=3,
            columns_json='["id"]',
            status="success",
            error=None,
            input_tokens=100,
            output_tokens=50,
            latency_ms=420,
            created_at=datetime.now(timezone.utc),
        )
        db.add(run)
        await db.flush()
        assert run.id is not None

        await db.refresh(run)
        assert run.question == "list all candidates"
        assert run.status == "success"
        assert run.row_count == 3
        assert run.columns_json == '["id"]'
        assert run.input_tokens == 100


def test_chatresult_defaults():
    result = ChatResult(
        status=ChatStatus.SUCCESS,
        answer="Two candidates found.",
        sql="SELECT id FROM candidates",
        execution=QueryExecution(ok=True),
        model_id="amazon.nova-lite-v1:0",
    )
    assert result.run_id == -1
    assert result.input_tokens == 0
    assert result.output_tokens == 0
    assert result.error is None
    assert result.suggestion is None


def test_query_execution_defaults():
    ok = QueryExecution(ok=True)
    assert ok.columns == []
    assert ok.rows == []
    assert ok.row_count == 0
    assert ok.error is None

    fail = QueryExecution(ok=False, error="column not found")
    assert not fail.ok
    assert fail.error == "column not found"


def test_chat_status_values():
    assert ChatStatus.SUCCESS.value == "success"
    assert ChatStatus.UNSAFE.value == "unsafe"
    assert ChatStatus.SQL_ERROR.value == "sql_error"
    assert ChatStatus.LLM_ERROR.value == "llm_error"

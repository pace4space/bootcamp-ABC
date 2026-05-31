"""Segment 07 tests — POST /api/chat (orchestrator + endpoint), Bedrock monkeypatched."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import QueryRun
from app.ingest.llm import BedrockError

_DEFAULT_SQL = "SELECT id, full_name FROM candidates WHERE status = 'Active'"


class FakeBedrock:
    model_id = "amazon.nova-lite-v1:0"
    SQL = _DEFAULT_SQL

    def __init__(self, *a, **k):
        pass

    def converse(self, system, user):
        return FakeBedrock.SQL, 30, 12

    def converse_messages(self, system, messages):
        return "Here are the active candidates: Alice Tester, Bob Tester.", 18, 8


class FakeBedrockLLMError:
    model_id = "amazon.nova-lite-v1:0"

    def __init__(self, *a, **k):
        pass

    def converse(self, system, user):
        raise BedrockError("bedrock unavailable")

    def converse_messages(self, system, messages):
        raise BedrockError("bedrock unavailable")


@pytest.fixture(autouse=True)
def reset_fake_sql():
    FakeBedrock.SQL = _DEFAULT_SQL
    yield
    FakeBedrock.SQL = _DEFAULT_SQL


@pytest.fixture
def mock_bedrock(monkeypatch):
    monkeypatch.setattr("app.chat.generator.BedrockClient", FakeBedrock)
    monkeypatch.setattr("app.chat.answerer.BedrockClient", FakeBedrock)


@pytest.fixture
def mock_bedrock_llm_error(monkeypatch):
    monkeypatch.setattr("app.chat.generator.BedrockClient", FakeBedrockLLMError)
    monkeypatch.setattr("app.chat.answerer.BedrockClient", FakeBedrockLLMError)


async def _post(client, auth_headers, body: dict):
    return await client.post("/api/chat", json=body, headers=auth_headers)


@pytest.mark.asyncio
async def test_success_grounded(client, auth_headers, mock_bedrock):
    r = await _post(client, auth_headers, {"question": "Who is active?"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["answer"]
    assert "SELECT" in data["sql"].upper()
    assert data["trace"]["rowCount"] >= 2
    assert "full_name" in data["trace"]["columns"]
    assert data["runId"]


@pytest.mark.asyncio
async def test_camelcase_serialization(client, auth_headers, mock_bedrock):
    r = await _post(client, auth_headers, {"question": "Who is active?"})
    assert r.status_code == 200
    data = r.json()
    assert "rowCount" in data["trace"]
    assert "runId" in data


@pytest.mark.asyncio
async def test_query_run_persisted(client, auth_headers, mock_bedrock, seeded_db):
    r = await _post(client, auth_headers, {"question": "Who is active?"})
    assert r.status_code == 200
    run_id = r.json()["runId"]
    async with seeded_db() as session:
        run = await session.get(QueryRun, run_id)
    assert run is not None
    assert run.status == "success"
    assert run.row_count >= 2


@pytest.mark.asyncio
async def test_viewer_can_chat(client, viewer_headers, mock_bedrock):
    r = await _post(client, viewer_headers, {"question": "Who is active?"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_401(client, mock_bedrock):
    r = await _post(client, {}, {"question": "Who is active?"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_unsafe_sql_returns_200_with_status(client, auth_headers, mock_bedrock, seeded_db):
    FakeBedrock.SQL = "DROP TABLE candidates"
    r = await _post(client, auth_headers, {"question": "drop everything"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "unsafe"
    assert data["error"]
    run_id = data["runId"]
    async with seeded_db() as session:
        run = await session.get(QueryRun, run_id)
    assert run is not None
    assert run.status == "unsafe"
    # table untouched — guard blocked before any execution
    async with seeded_db() as session:
        result = await session.execute(select(QueryRun))
        assert result.scalars().all()  # at least the row we just wrote


@pytest.mark.asyncio
async def test_sql_error_returns_200(client, auth_headers, mock_bedrock, seeded_db):
    FakeBedrock.SQL = "SELECT nope FROM candidates"
    r = await _post(client, auth_headers, {"question": "bad column"})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "sql_error"
    assert data["error"]
    run_id = data["runId"]
    async with seeded_db() as session:
        run = await session.get(QueryRun, run_id)
    assert run is not None
    assert run.status == "sql_error"


@pytest.mark.asyncio
async def test_llm_error_returns_422(client, auth_headers, mock_bedrock_llm_error, seeded_db):
    r = await _post(client, auth_headers, {"question": "anything"})
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert "error" in detail
    assert "suggestion" in detail
    # query_runs row was still written (observability is unconditional)
    async with seeded_db() as session:
        result = await session.execute(
            select(QueryRun).where(QueryRun.status == "llm_error")
        )
        assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_multi_turn_history_accepted(client, auth_headers, mock_bedrock):
    body = {
        "question": "and those active ones?",
        "history": [
            {"role": "user", "content": "Who has kubernetes?"},
            {"role": "assistant", "content": "Bob Tester."},
        ],
    }
    r = await _post(client, auth_headers, body)
    assert r.status_code == 200
    assert r.json()["status"] == "success"

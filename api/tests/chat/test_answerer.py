"""Segment 06 tests — answer synthesizer (grounded, multi-turn)."""
from __future__ import annotations

import pytest

from app.chat.answerer import _NO_ROWS, synthesize_answer
from app.chat.types import ChatTurn, QueryExecution


class FakeBedrock:
    model_id = "amazon.nova-lite-v1:0"

    def __init__(self, reply="Two candidates: Alice, Bob."):
        self.reply = reply
        self.seen = None

    def converse_messages(self, system, messages):
        self.seen = (system, messages)
        return self.reply, 20, 9


def _exec_with_rows(rows: list) -> QueryExecution:
    return QueryExecution(ok=True, columns=list(rows[0].keys()) if rows else [], rows=rows, row_count=len(rows))


@pytest.mark.asyncio
async def test_empty_rows_short_circuits():
    fake = FakeBedrock()
    execution = QueryExecution(ok=True, columns=["id"], rows=[], row_count=0)
    answer, in_tok, out_tok = await synthesize_answer("any question", execution, bedrock_client=fake)
    assert answer == _NO_ROWS
    assert in_tok == 0
    assert out_tok == 0
    assert fake.seen is None  # Bedrock was never called


@pytest.mark.asyncio
async def test_grounded_answer_returned():
    fake = FakeBedrock()
    execution = _exec_with_rows([{"id": "cv_t01", "full_name": "Alice"}])
    answer, in_tok, out_tok = await synthesize_answer("Who is active?", execution, bedrock_client=fake)
    assert answer == fake.reply
    assert in_tok == 20
    assert out_tok == 9


@pytest.mark.asyncio
async def test_rows_json_in_user_turn():
    fake = FakeBedrock()
    execution = _exec_with_rows([{"id": "cv_t01", "full_name": "Alice"}])
    await synthesize_answer("Who is active?", execution, bedrock_client=fake)
    _, messages = fake.seen
    last = messages[-1]
    assert last["role"] == "user"
    assert "Alice" in last["content"]


@pytest.mark.asyncio
async def test_history_becomes_conversation_entries():
    fake = FakeBedrock()
    history = [ChatTurn("user", "q1"), ChatTurn("assistant", "a1")]
    execution = _exec_with_rows([{"id": "cv_t01", "full_name": "Alice"}])
    await synthesize_answer("Who is active?", execution, history=history, bedrock_client=fake)
    _, messages = fake.seen
    assert len(messages) == 3
    assert messages[0] == {"role": "user", "content": "q1"}
    assert messages[1] == {"role": "assistant", "content": "a1"}
    assert messages[2]["role"] == "user"


@pytest.mark.asyncio
async def test_system_prompt_loaded():
    fake = FakeBedrock()
    execution = _exec_with_rows([{"id": "cv_t01"}])
    await synthesize_answer("test", execution, bedrock_client=fake)
    system, _ = fake.seen
    assert "ONLY the rows" in system or "only the rows" in system.lower()
    assert "no matching records" in system.lower()

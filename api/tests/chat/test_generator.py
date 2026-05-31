"""Segment 03 tests — SQL generation (no network, FakeBedrock injected)."""
from __future__ import annotations

import pytest

from app.chat.generator import generate_sql
from app.chat.types import ChatTurn


class FakeBedrock:
    model_id = "amazon.nova-lite-v1:0"

    def __init__(self, reply: str = "SELECT 1"):
        self._reply = reply
        self.last_system = ""
        self.last_user = ""

    def converse(self, system: str, user: str) -> tuple:
        self.last_system, self.last_user = system, user
        return self._reply, 11, 7


async def test_strips_sql_fences():
    fake = FakeBedrock("```sql\nSELECT 1\n```")
    result = await generate_sql("how many candidates?", bedrock_client=fake)
    assert result.sql == "SELECT 1"


async def test_passes_through_plain_sql():
    fake = FakeBedrock("SELECT id FROM candidates")
    result = await generate_sql("list candidates", bedrock_client=fake)
    assert result.sql == "SELECT id FROM candidates"
    assert result.input_tokens == 11
    assert result.output_tokens == 7


async def test_prompt_text_contains_system_and_user():
    fake = FakeBedrock("SELECT 1")
    result = await generate_sql("show open positions", bedrock_client=fake)
    assert "[SYSTEM]" in result.prompt_text
    assert "show open positions" in result.prompt_text


async def test_history_folded_into_user():
    fake = FakeBedrock("SELECT 1")
    history = [
        ChatTurn("user", "show open positions"),
        ChatTurn("assistant", "There are 3 open positions."),
    ]
    await generate_sql("which ones have no applicants?", history=history, bedrock_client=fake)
    assert "Previous turns:" in fake.last_user
    assert "Current question:" in fake.last_user


async def test_model_id_comes_from_client():
    fake = FakeBedrock("SELECT 1")
    result = await generate_sql("q", bedrock_client=fake)
    assert result.model_id == "amazon.nova-lite-v1:0"

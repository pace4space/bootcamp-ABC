"""Segment 06 tests — grounded match explainer."""
from __future__ import annotations

import types

import pytest

from app.embeddings.explainer import explain_match


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _skill(name):
    return types.SimpleNamespace(name=name, sort_order=0)

def _exp(role, company, start_year=2020):
    return types.SimpleNamespace(role=role, company=company, start_year=start_year)

def _req(text, req_type="must_have", sort_order=0):
    return types.SimpleNamespace(text=text, type=req_type, sort_order=sort_order)

def _candidate(**kw):
    defaults = dict(headline="Engineer", skills=[], experience=[], education=[], languages=[])
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)

def _position(**kw):
    defaults = dict(title="Role", requirements=[])
    defaults.update(kw)
    return types.SimpleNamespace(**defaults)


class _MockBedrockClient:
    model_id = "test-model"
    embed_model_id = "mock-titan"
    _last_system: str = ""
    _last_user: str = ""

    def __init__(self, reply: str = "Good fit because of shared Python skills.") -> None:
        self._reply = reply

    def converse(self, system: str, user: str) -> tuple[str, int, int]:
        _MockBedrockClient._last_system = system
        _MockBedrockClient._last_user = user
        return self._reply, 50, 20


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_prompt_contains_candidate_skills():
    c = _candidate(
        headline="Platform Engineer",
        skills=[_skill("Kubernetes"), _skill("Terraform")],
    )
    p = _position(title="DevOps Role", requirements=[_req("Kubernetes")])
    client = _MockBedrockClient()

    await explain_match(c, p, 0.72, client=client)

    assert "Kubernetes" in _MockBedrockClient._last_user
    assert "Terraform" in _MockBedrockClient._last_user


async def test_prompt_contains_position_requirements():
    c = _candidate(skills=[_skill("Python")])
    p = _position(
        title="Backend Engineer",
        requirements=[
            _req("FastAPI", "must_have"),
            _req("PostgreSQL", "nice_to_have"),
        ],
    )
    client = _MockBedrockClient()

    await explain_match(c, p, 0.65, client=client)

    assert "FastAPI" in _MockBedrockClient._last_user
    assert "PostgreSQL" in _MockBedrockClient._last_user


async def test_system_prompt_forbids_invention():
    c = _candidate()
    p = _position()
    client = _MockBedrockClient()

    await explain_match(c, p, 0.5, client=client)

    sys = _MockBedrockClient._last_system.lower()
    assert "invent" in sys or "only" in sys   # anti-hallucination instruction present


async def test_returns_explanation_and_tokens():
    c = _candidate(skills=[_skill("Python")])
    p = _position(requirements=[_req("Python")])
    client = _MockBedrockClient(reply="The candidate's Python experience directly matches the role.")

    explanation, in_tok, out_tok = await explain_match(c, p, 0.8, client=client)

    assert len(explanation) > 0
    assert in_tok == 50
    assert out_tok == 20


async def test_no_overlap_still_returns_sentence():
    c = _candidate(skills=[_skill("React")])
    p = _position(requirements=[_req("Kubernetes")])
    client = _MockBedrockClient(reply="The match is weak; no shared skills found.")

    explanation, _, _ = await explain_match(c, p, 0.51, client=client)

    assert len(explanation) > 0   # model returns weak-match sentence, not empty

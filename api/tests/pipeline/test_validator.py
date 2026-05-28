"""Unit tests for pipeline/validator.py.

Operates only on LLMResponse + HeuristicHints — no DB, no LLM calls.
"""
from __future__ import annotations

import json

import pytest

from app.pipeline.types import ExtractionStatus, HeuristicHints, LLMResponse
from app.pipeline.validator import ValidationError, validate_cv_payload, validate_position_payload

VALID_CV_JSON = json.dumps({
    "full_name": "Alice Smith",
    "headline": "Senior DevOps Engineer",
    "summary": "Experienced engineer.",
    "skills": ["AWS", "Docker"],
    "experience": [{"role": "SRE", "company": "Acme", "start_year": 2020}],
    "education": [],
    "certifications": [],
    "languages": [],
})

VALID_POSITION_JSON = json.dumps({
    "title": "Backend Engineer",
    "description": "Build APIs.",
    "requirements": [{"type": "must_have", "text": "Python"}],
})


def _cv_resp(raw_json: str) -> LLMResponse:
    return LLMResponse(
        model_id="test-model",
        prompt_version="cv-v1",
        prompt_text="...",
        raw_json_str=raw_json,
        input_tokens=10,
        output_tokens=5,
        latency_ms=100,
    )


# ---------------------------------------------------------------------------
# validate_cv_payload — success path
# ---------------------------------------------------------------------------

def test_valid_json_returns_payload_with_success_status():
    payload, warnings, status = validate_cv_payload(_cv_resp(VALID_CV_JSON), HeuristicHints())
    assert payload.full_name == "Alice Smith"
    assert payload.experience[0].start_year == 2020
    assert warnings == []
    assert status == ExtractionStatus.SUCCESS


def test_hints_email_overrides_llm_email_silently():
    d = {**json.loads(VALID_CV_JSON), "email": "llm@bad.com"}
    payload, warnings, _ = validate_cv_payload(
        _cv_resp(json.dumps(d)), HeuristicHints(email="regex@good.com")
    )
    assert payload.email == "regex@good.com"
    # Override is silent — no warning should mention email
    assert not any("email" in w for w in warnings)


# ---------------------------------------------------------------------------
# validate_cv_payload — structural failures → ValidationError
# ---------------------------------------------------------------------------

def test_missing_full_name_raises_validation_error():
    d = {k: v for k, v in json.loads(VALID_CV_JSON).items() if k != "full_name"}
    with pytest.raises(ValidationError, match="full_name"):
        validate_cv_payload(_cv_resp(json.dumps(d)), HeuristicHints())


def test_malformed_json_raises_validation_error():
    with pytest.raises(ValidationError, match="JSON"):
        validate_cv_payload(_cv_resp("{bad json}"), HeuristicHints())


# ---------------------------------------------------------------------------
# validate_cv_payload — type coercion → warning + PARTIAL
# ---------------------------------------------------------------------------

def test_string_start_year_cast_to_int_appends_warning_and_partial():
    d = json.loads(VALID_CV_JSON)
    d["experience"][0]["start_year"] = "2019"
    payload, warnings, status = validate_cv_payload(_cv_resp(json.dumps(d)), HeuristicHints())
    assert payload.experience[0].start_year == 2019
    assert any("start_year" in w for w in warnings)
    assert status == ExtractionStatus.PARTIAL


# ---------------------------------------------------------------------------
# validate_position_payload — minimal coverage
# ---------------------------------------------------------------------------

def test_valid_position_json_returns_payload():
    resp = LLMResponse(
        model_id="test-model", prompt_version="position-v1", prompt_text="...",
        raw_json_str=VALID_POSITION_JSON, input_tokens=10, output_tokens=5, latency_ms=50,
    )
    payload, warnings, status = validate_position_payload(resp, HeuristicHints())
    assert payload.title == "Backend Engineer"
    assert len(payload.requirements) == 1
    assert warnings == []
    assert status == ExtractionStatus.SUCCESS


def test_missing_title_raises_validation_error():
    bad = json.dumps({"description": "no title here"})
    resp = LLMResponse(
        model_id="test-model", prompt_version="position-v1", prompt_text="...",
        raw_json_str=bad, input_tokens=10, output_tokens=5, latency_ms=50,
    )
    with pytest.raises(ValidationError, match="title"):
        validate_position_payload(resp, HeuristicHints())

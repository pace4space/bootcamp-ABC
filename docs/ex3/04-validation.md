# Ex3 — Module 4: LLM Output Validation

## Problem

The LLM returns a string. We need a structured `CandidatePayload` or `PositionPayload`
with type-safe fields validated against our schema. The LLM can be wrong in two distinct
ways: structurally (malformed JSON, missing required fields) and semantically (a year stored
as a string, a skills list as a comma-separated string instead of an array).

## Failure Taxonomy

| Failure type | Example | Outcome |
|---|---|---|
| Malformed JSON | `{name: "Alice"` (no closing brace) | `ValidationError` → pipeline FAILED |
| Missing required field | No `full_name` in JSON | `ValidationError` → pipeline FAILED |
| Type mismatch on optional field | `start_year: "2019"` (string not int) | Cast attempt; warning if cast succeeds; field `None` + warning if cast fails → pipeline PARTIAL |
| Heuristic override | LLM email ≠ hints email | Hints win silently (expected behavior, no warning) |

## The PARTIAL Status

`PARTIAL` means: an entity was created and stored, but not all fields extracted cleanly.
The entity is usable (appears in candidate lists, assignable to positions) but has holes.
`extraction_runs.warnings` explains what was lost.

This is preferable to rejecting the entire document because one experience entry had a
malformed date. A candidate with 9/10 fields correct is more useful than no candidate.

Callers receive HTTP 201 with warnings in the response body. The agent in Ex6 can choose
to flag PARTIAL candidates for human review.

## Heuristic Override Logic

```python
def _apply_hints(payload_dict: dict, hints: HeuristicHints) -> dict:
    """Heuristic values override LLM values for the same field."""
    overrides = {k: v for k, v in asdict(hints).items() if v is not None}
    return {**payload_dict, **overrides}
```

Simple dict merge where hints win. Explicit in code, logged in the prompt context,
and immediately explainable in code review.

## Why Not Pydantic for LLM Output Validation?

We _could_ call `CandidatePayload.model_validate(json.loads(raw_json))`. But Pydantic
raises `ValidationError` on the first failure and gives no access to partial results.
We want to extract as much as possible and collect all failures as warnings.

**Rule:** Pydantic belongs at API boundaries (what we return to clients). Pipeline
internal types use plain dataclasses with manual field-by-field validation, giving us
granular error collection.

## Public Interface

```python
# api/app/pipeline/validator.py

class ValidationError(Exception):
    """Raised when LLM output is structurally invalid (bad JSON or missing required fields)."""

def validate_cv_payload(
    llm_response: LLMResponse,
    hints: HeuristicHints,
) -> tuple[CandidatePayload, list[str]]:
    """
    Parse LLM JSON string → CandidatePayload.
    Apply heuristic overrides.
    Returns (payload, warnings). warnings is non-empty on partial extraction.
    Raises ValidationError if JSON is unparseable or required fields absent.
    """

def validate_position_payload(
    llm_response: LLMResponse,
    hints: HeuristicHints,
) -> tuple[PositionPayload, list[str]]:
    ...
```

## Test Cases

```python
# tests/pipeline/test_validator.py

VALID_CV_JSON = json.dumps({
    "full_name": "Alice Smith",
    "headline": "Senior DevOps Engineer",
    "summary": "...",
    "skills": ["AWS", "Docker", "Kubernetes"],
    "experience": [{"role": "SRE", "company": "Acme", "start_year": 2020}],
    "education": [],
})

def test_valid_json_returns_payload():
    resp = _make_llm_response(VALID_CV_JSON)
    payload, warnings = validate_cv_payload(resp, HeuristicHints())
    assert payload.full_name == "Alice Smith"
    assert warnings == []

def test_hints_email_overrides_llm_email():
    json_with_email = json.dumps({**json.loads(VALID_CV_JSON), "email": "llm@bad.com"})
    resp = _make_llm_response(json_with_email)
    hints = HeuristicHints(email="regex@good.com")
    payload, _ = validate_cv_payload(resp, hints)
    assert payload.email == "regex@good.com"

def test_missing_full_name_raises_validation_error():
    bad = {k: v for k, v in json.loads(VALID_CV_JSON).items() if k != "full_name"}
    resp = _make_llm_response(json.dumps(bad))
    with pytest.raises(ValidationError, match="full_name"):
        validate_cv_payload(resp, HeuristicHints())

def test_string_year_becomes_warning():
    with_str_year = json.loads(VALID_CV_JSON)
    with_str_year["experience"][0]["start_year"] = "2020"
    resp = _make_llm_response(json.dumps(with_str_year))
    payload, warnings = validate_cv_payload(resp, HeuristicHints())
    assert payload.experience[0].start_year == 2020
    assert any("start_year" in w for w in warnings)

def test_malformed_json_raises_validation_error():
    resp = _make_llm_response("{bad json}")
    with pytest.raises(ValidationError, match="JSON"):
        validate_cv_payload(resp, HeuristicHints())
```

## Interview Talking Point

> "Why distinguish between FAILED and PARTIAL at the pipeline level rather than letting the caller decide?"

Because the caller (HTTP handler, agent) needs to distinguish "nothing was created, please
retry" from "something was created, check warnings before proceeding." These require
different actions. Encoding the distinction in the type system makes it impossible to handle
them the same way by accident.

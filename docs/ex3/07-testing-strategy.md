# Ex3 — Module 7: Testing Strategy

## Principle: Test the Boundaries, Not the Middle

Each stage has exactly one input type and one output type. Unit tests operate at those
boundaries. The test for `heuristics.py` takes a `RawDocument` and asserts `HeuristicHints`.
It does not care about the parser. The test for the validator takes an `LLMResponse` and
asserts a `CandidatePayload`. It does not care about the LLM client.

Integration tests (endpoint tests) mock only at the outermost injected boundary:
`BedrockClient.converse`. Every other stage runs with real code.

## Test Pyramid

```
                    ┌─────────────────────────┐
                    │   Integration (1 file)   │  ← endpoint tests, Bedrock mocked
                    └────────────┬────────────┘
              ┌─────────────────┴─────────────────┐
              │        DB-backed unit tests (2)    │  ← persister, logger (SQLite)
              └────────────────┬──────────────────┘
    ┌──────────────────────────┴──────────────────────────┐
    │              Pure unit tests (4)                     │  ← parsers, heuristics, llm, validator
    └─────────────────────────────────────────────────────┘
```

## Test File Structure

```
api/tests/pipeline/
├── conftest.py                  # fixtures: minimal PDF/DOCX, canned LLM JSON, mock client
├── test_parsers.py              # parse_cv + parse_position unit tests
├── test_heuristics.py           # extract_hints parameterized tests
├── test_llm.py                  # BedrockClient mocked; prompt loading; token capture
├── test_validator.py            # validate_cv_payload unit tests
├── test_persister.py            # persist_candidate with seeded_db fixture
├── test_logger.py               # log_raw_document + log_extraction_run
└── test_ingest_endpoints.py     # full endpoint tests with mocked BedrockClient
```

## Mocking Strategy for Bedrock

**Option A (preferred) — inject via optional parameter:**
```python
class MockBedrockClient:
    model_id = "test-model"
    def converse(self, system_prompt: str, user_message: str) -> tuple[str, int, int]:
        return (CANNED_CV_JSON, 100, 50)

result = await run_cv_pipeline(
    pdf_bytes, "test.pdf", db,
    bedrock_client=MockBedrockClient()
)
```

Preferred because the dependency is explicit in the function signature. No import-path
patching, no monkey-patching module globals.

**Option B — monkeypatch fallback:**
```python
monkeypatch.setattr("app.pipeline.llm.BedrockClient", lambda **kw: MockBedrockClient())
```

Use when testing through the endpoint (can't pass the client directly).

## Key Test Cases by Stage

### Parsers
- PDF bytes → non-empty `RawDocument.raw_text`
- DOCX bytes → non-empty `RawDocument.raw_text`
- Empty PDF → `ParseError` raised
- Unknown extension (`.rtf`) → `ParseError` raised
- Position TXT string → `RawDocument` with `kind=POSITION`

### Heuristics
- Email in text → `hints.email` set
- Israeli phone `050-1234567` → `hints.phone` set
- LinkedIn URL → `hints.linkedin_url` set
- `From: mgr@co.com` in position text → `hints.hiring_manager_email` set
- No patterns in text → all fields `None`

### LLM Client
- `BedrockClient.converse` (mocked) → `LLMResponse` with correct token counts
- Correct prompt version file loaded (`cv-v1.txt` exists and is read)
- `{heuristic_hints_json}` present in rendered prompt text
- Mocked `BedrockError` → `BedrockError` re-raised by `call_llm_for_cv`

### Validator
- Valid JSON → `CandidatePayload` with correct fields, empty warnings
- Hints email overrides LLM email
- Missing `full_name` → `ValidationError`
- String year `"2019"` → cast to `2019`, warning emitted
- Malformed JSON → `ValidationError`

### Persister (DB-backed)
- Full candidate with skills + experience → all rows in DB
- Duplicate email → `IntegrityError` raised
- Candidate with no children → `Candidate` row still created

### Logger (DB-backed)
- `log_raw_document` returns integer ID, row is queryable
- `log_extraction_run` with `status=FAILED`, `entity_id=None` persists correctly
- `errors` and `warnings` arrays stored and retrievable

### Endpoint Integration
- `POST /api/ingest/cv` + valid PDF + mocked Bedrock → 201, `entity_id` starts with `cv_`
- New candidate retrievable at `GET /api/candidates/{entity_id}`
- Mocked `BedrockError` → 422 with errors list
- `.txt` file to `/ingest/cv` → 422 (wrong MIME, before pipeline runs)
- Unauthenticated request → 401
- Viewer role → 403 (admin/recruiter required)

## No Real Bedrock in Automated Tests

Three reasons, all non-negotiable:
1. Tests must run without AWS credentials (CI, other machines, bootcamp environments)
2. Real LLM calls are non-deterministic — a test passing today may fail tomorrow
3. Real LLM calls cost money — the test suite must be free to run

The end-to-end real Bedrock call lives in **Step 9** as a manual verification, not an
automated test.

## Running the Full Suite

```bash
# All pipeline tests
cd api && pytest tests/pipeline/ -v

# Full suite (pipeline + existing Ex2 tests — no regressions)
pytest tests/ -v

# Just unit tests (no DB required, no network)
pytest tests/pipeline/test_parsers.py tests/pipeline/test_heuristics.py \
       tests/pipeline/test_llm.py tests/pipeline/test_validator.py -v
```

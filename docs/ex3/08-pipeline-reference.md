# Ex3 — Pipeline Reference

## Audience

This reference is for engineers wiring the ingestion pipeline into FastAPI, tests, or
future agent workflows. The module design docs explain the reasoning; this file documents
the callable contracts that should stay synchronized with code.

## Source Of Truth

| Concern | File |
|---------|------|
| Orchestration | `api/app/pipeline/__init__.py` |
| Shared dataclasses and enums | `api/app/pipeline/types.py` |
| Parsing | `api/app/pipeline/parsers.py` |
| Deterministic hints | `api/app/pipeline/heuristics.py` |
| Bedrock prompt calls | `api/app/pipeline/llm.py` |
| Validation | `api/app/pipeline/validator.py` |
| Persistence | `api/app/pipeline/persister.py` |
| Run logging | `api/app/pipeline/logger.py` |
| HTTP endpoints | `api/app/routers/ingest.py` |

## Public Orchestrators

```python
async def run_cv_pipeline(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
    bedrock_client=None,
) -> ExtractionResult: ...

async def run_position_pipeline(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
    bedrock_client=None,
) -> ExtractionResult: ...
```

Both orchestrators run:

```text
parse -> extract_hints -> call_llm -> validate -> log raw document -> persist -> log run
```

`bedrock_client` is injectable for tests. Production callers omit it and the pipeline
constructs a `BedrockClient` using `BEDROCK_MODEL_ID` and `BEDROCK_REGION`.

## Accepted Inputs

| Pipeline | Allowed formats | Parser behavior |
|----------|-----------------|-----------------|
| CV | `.pdf`, `.docx` | PDF bytes are parsed with `pdfminer.six`; DOCX bytes are parsed with `python-docx` paragraphs joined by newline. |
| Position | `.txt` | Bytes are decoded as UTF-8 with replacement for malformed sequences. |

Unsupported extensions raise `ParseError`. A supported file that produces empty text after
`strip()` also raises `ParseError`.

## Return Contract

The final return value is `ExtractionResult`:

| Field | Meaning |
|-------|---------|
| `status` | `success`, `partial`, or `failed` |
| `document_kind` | `cv` or `position` |
| `raw_document_id` | `raw_documents.id`; current orchestrators return this only after logging succeeds |
| `extraction_run_id` | `extraction_runs.id`; current orchestrators return this only after logging succeeds |
| `entity_id` | Created candidate or position id, or `None` on failed validation |
| `errors` | Structural failures that prevent entity creation |
| `warnings` | Coercions or skipped nested items that still allow persistence |
| `input_tokens`, `output_tokens`, `model_id` | LLM accounting copied from `LLMResponse` |

## HTTP Contract

`api/app/routers/ingest.py` exposes:

```text
POST /api/ingest/cv
POST /api/ingest/position
```

Both endpoints require an authenticated `admin` or `recruiter`, accept a multipart file
upload, run the matching orchestrator, commit once, and return `201 Created` with:

```json
{
  "status": "success",
  "entity_id": "cv_abc123ef",
  "run_id": 42,
  "input_tokens": 1234,
  "output_tokens": 456,
  "warnings": [],
  "errors": []
}
```

`ParseError` and unexpected LLM-layer exceptions are translated to `422 Unprocessable
Entity`. Validation failures return a normal `201` response with `status: "failed"` when a
raw document and extraction run can be logged.

## Heuristic Override Rules

`extract_hints(doc)` returns `HeuristicHints` with optional values:

```text
email, phone, linkedin_url, github_url, hiring_manager_email
```

During validation, non-null hints override fields returned by the LLM. This is intentional
and silent: warnings are reserved for unexpected data-shape degradation, not for trusted
regex wins.

## Status Semantics

| Status | Entity created? | Typical cause |
|--------|-----------------|---------------|
| `success` | Yes | Valid LLM JSON and no validation warnings |
| `partial` | Yes | Recoverable coercions, skipped malformed nested rows, or missing optional data |
| `failed` | No | Structural validation failure such as malformed JSON or missing required `full_name`/`title` |

Parse and Bedrock failures do not currently produce `ExtractionResult`; they propagate to
the HTTP layer as `422`.

## Persistence And Logging

Candidate IDs are generated as `cv_<8 hex chars>` and position IDs as `job_<8 hex chars>`.
Entity writes use nested transactions so each candidate or position and its child rows land
atomically inside the request transaction.

`raw_documents` stores the parsed text and metadata. `extraction_runs` stores prompt
version, full rendered prompt, raw LLM output, status, entity id, warnings, errors, token
counts, and latency. The endpoint performs the outer commit after the pipeline returns.

## Test Coverage Map

| Contract | Tests |
|----------|-------|
| Parser format guards and empty-text failures | `api/tests/pipeline/test_parsers.py` |
| Regex hints and no-match behavior | `api/tests/pipeline/test_heuristics.py` |
| Bedrock wrapper and prompt rendering | `api/tests/pipeline/test_llm.py` |
| Validation status, coercion, and hint overrides | `api/tests/pipeline/test_validator.py` |
| Atomic persistence | `api/tests/pipeline/test_persister.py` |
| Raw document and extraction run logging | `api/tests/pipeline/test_logger.py` |
| HTTP endpoint translation | `api/tests/pipeline/test_ingest_endpoints.py` |

# Ex3 — Exercise Overview & Architecture

## Purpose

This exercise closes the gap between "we have data" and "we can produce data." It transforms
Hellio HR from a system that reads pre-curated records into one that can **ingest raw documents**
and produce structured, queryable candidates and positions.

## The Three Principles of an Ingestion Pipeline

### 1. Separation: parsing ≠ extraction ≠ persistence
These are three distinct concerns. Parsing is I/O (bytes → text). Extraction is interpretation
(text → fields). Persistence is I/O again (fields → DB rows). Coupling any two makes the
others untestable and failures unlocatable.

### 2. Trust hierarchy: heuristics > LLM > null
Not all extraction is equally reliable. An email regex on a structured field is deterministic
and auditable. An LLM inferring seniority from prose is probabilistic. The pipeline reflects
this: heuristics run first, their results lock in, and the LLM fills the gaps. When both
sources produce a value for the same field, the heuristic wins.

### 3. Observability by default
Every pipeline invocation produces two DB rows: one for the raw document text, one for the
extraction run. Written unconditionally — success, partial failure, or total failure.
A pipeline that only logs success is not observable; it is a black box.

## What We Have Entering Ex3

- 270 CV files (PDF/DOCX) in `public/cvs/`
- 20 job email files (TXT) in `public/jobs/`
- 12 manually extracted candidates + 20 positions (ground truth to compare against)
- Running FastAPI + Postgres backend with known schema (Ex2)

## What We Produce

- A `pipeline/` module with 7 submodules, each independently testable
- Two new API endpoints: `POST /api/ingest/cv` and `POST /api/ingest/position`
- Two new DB tables: `raw_documents` and `extraction_runs`
- Versioned prompts in `pipeline/prompts/`
- Full test coverage with Bedrock mocked in all automated tests

## Architecture Diagram

```
POST /api/ingest/cv        (multipart, PDF or DOCX)
POST /api/ingest/position  (multipart, TXT)
          │
          ▼
   api/app/pipeline/
   ┌─────────────────────────────────────────────────────────────┐
   │  run_cv_pipeline(bytes, filename, db) → ExtractionResult    │
   │                                                             │
   │  Stage 1: parsers.py    → RawDocument (raw_text)           │
   │  Stage 2: heuristics.py → HeuristicHints (regex winners)   │
   │  Stage 3: llm.py        → LLMResponse (raw JSON + tokens)  │
   │  Stage 4: validator.py  → CandidatePayload + warnings       │
   │  Stage 5: persister.py  → entity_id (DB write, atomic)     │
   │  Stage 6: logger.py     → raw_documents + extraction_runs  │
   └─────────────────────────────────────────────────────────────┘
          │
          ▼
   IngestResponse (status, entity_id, run_id, tokens, errors)
```

Data flows forward through types, never backward. No stage imports from another stage
except via `types.py`.

## Architecture Decision: Why a Module, Not a Script

A CLI script would work for Ex3. But Ex6 introduces an HR agent that ingests documents
mid-workflow. A standalone script can't be called from FastAPI. Making the pipeline a proper
module from the start means Ex6 calls `run_cv_pipeline()` the same way the ingest endpoint
does. The investment in a typed, staged pipeline pays forward across four exercises.

## Module Learning Map

| Module | Core Lesson |
|--------|-------------|
| `types.py` | Typed boundaries between stages eliminate implicit coupling |
| `parsers.py` | Parsing is I/O, not extraction. An empty result is a failure, not "no data" |
| `heuristics.py` | Regex is not legacy — it's the right tool for high-signal structured fields |
| `llm.py` | Third-party clients are injected dependencies. Prompts are versioned artifacts |
| `validator.py` | LLM output is untrusted input. Distinguish FAILED from PARTIAL |
| `persister.py` | Persistence is a transaction boundary. Atomicity is the contract |
| `logger.py` | Every run — success or failure — must be inspectable after the fact |
| `ingest.py` | HTTP is a translation layer: domain outcomes → status codes, nothing else |

## Carry-Forward to Ex4–Ex6

- **Ex4** (deterministic search): `extraction_runs` has cost data per run; will surface as a reporting endpoint
- **Ex5** (embeddings): `raw_documents.raw_text` is the embedding input — no re-parsing needed
- **Ex6** (HR agent): `run_cv_pipeline()` is a callable function; the agent calls it the same way the endpoint does

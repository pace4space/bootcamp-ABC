# Exercise 3 — Submission

## What Ex3 Delivers

A 6-stage LLM extraction pipeline that ingests raw PDF and DOCX CVs (plus TXT job
emails) and produces structured, queryable candidates and positions in the existing
Postgres schema. The pipeline runs end-to-end via two new API endpoints
(`POST /api/ingest/cv`, `POST /api/ingest/position`) protected by the existing
admin/recruiter JWT roles. Every invocation writes two observability rows to new
`raw_documents` and `extraction_runs` tables regardless of outcome — success,
partial, or failure. Heuristics (regex: email, phone, LinkedIn, GitHub) lock in
before the LLM call; the LLM fills semantic fields (name, skills, experience,
summary); validation tolerates per-field type mismatches with PARTIAL status rather
than discarding the document; persistence uses savepoints for atomicity. All stages
are independently unit-tested with Bedrock mocked; the end-to-end live call is the
Step 9 manual verification below.

---

## Pipeline Architecture

```
POST /api/ingest/cv  (multipart PDF/DOCX)
         │
         ▼
Stage 1: parsers.py     → RawDocument (raw_text, char_count)
Stage 2: heuristics.py  → HeuristicHints (email, phone, linkedin_url, github_url)
Stage 3: llm.py         → LLMResponse (Bedrock converse(), input_tokens, output_tokens)
Stage 4: validator.py   → CandidatePayload + warnings  [SUCCESS | PARTIAL | FAILED]
Stage 5: persister.py   → entity_id  cv_<8hex>  (begin_nested savepoint)
Stage 6: logger.py      → raw_documents + extraction_runs rows (flush only)
         │
         ▼
IngestResponse { status, entityId, runId, inputTokens, outputTokens, warnings, errors }
```

Trust hierarchy: **heuristics > LLM > null**. Heuristic values override LLM values
silently for structured contact fields. PARTIAL status means the entity was created
but has warnings; FAILED means nothing was persisted (safe to retry).

---

## Artifact 1 — Test Suite

**99/99 tests green** across all pipeline stages:

| Step | Module | Tests |
|------|--------|-------|
| 1 | types.py + ORM models + Alembic 0002 | 36/36 (regression) |
| 2 | parsers.py | 12/12 |
| 3 | heuristics.py | 19/19 |
| 4 | llm.py + prompts/ | 8/8 |
| 5 | validator.py | 7/7 |
| 6 | logger.py | 5/5 |
| 7 | persister.py | 6/6 |
| 8 | orchestrator + ingest endpoints | 6/6 |

---

## Artifact 2 — Git Log (ex3 ^ master)

```
1de6555 chore: session-end hook auto-update — commits
16bff9b docs: update PROGRESS.md + session note — Ex3 Steps 0–8 complete, Step 9 remaining
db3d9b4 feat: Ex3 Step 8 — orchestrator + ingest endpoint, 6/6 tests, 99/99 total
7d689c5 feat: Ex3 Step 7 — persister.py, 6/6 tests passing
24cb8e0 feat: Ex3 Step 6 — logger.py, 5/5 tests passing
92b1e9f feat: Ex3 Step 5 — validator.py, 7/7 tests passing
0089c8f feat: Ex3 Step 4 — LLM client + versioned prompts, 8/8 tests passing
377a817 feat: Ex3 Step 3 — heuristic extractor, 19/19 tests passing
8d51c6b feat: Ex3 Step 2 — document parsers, 12/12 tests passing
9089e3a feat: Ex3 Step 0+1 — mini-plans, DB models, pipeline types
43d0031 chore: .claude tooling — session-end hook, post-commit path fix, skill update
2aa2c0b docs: reorganize into per-exercise subdirectories
```

---

## Artifact 3 — Step 9 Live Bedrock Verification

**Model:** `amazon.nova-lite-v1:0` (us-east-1)
**Test CV:** `cv_013.pdf` (Adeline Cordova — not in seed data)

### Criterion 1 — POST /api/ingest/cv → 201, cv_ entityId

```json
{
    "status": "success",
    "entityId": "cv_f241460e",
    "runId": 1,
    "inputTokens": 834,
    "outputTokens": 556,
    "warnings": [],
    "errors": []
}
```
✅ HTTP 201, `entityId` starts with `cv_`, 834 input tokens consumed.

### Criterion 2 — GET /api/candidates/cv_f241460e → 200, full candidate

```json
{
    "id": "cv_f241460e",
    "fullName": "Adeline Cordova",
    "headline": "IT Support Specialist",
    "status": "Active",
    "contact": {
        "email": "adeline.cordova@email.com",
        "phone": "060-1354794",
        "city": "Rishon LeZion"
    },
    "summary": "IT Support Specialist with 3 years of hands-on experience...",
    "skills": ["active directory", "azure", "bash", "centos", "docker",
               "git", "linux", "network basics", "networking",
               "powershell scripting", "ubuntu", "windows server"],
    "experience": [3 entries, sorted desc by startYear],
    "education": [{"degree": "Practical Engineer - Electronics", ...}]
}
```
✅ HTTP 200, complete candidate object with all extracted fields.

### Criterion 3 — extraction_runs row has input_tokens > 0

```
 id | status  | input_tokens | output_tokens |  entity_id
----+---------+--------------+---------------+-------------
  1 | success |          834 |           556 | cv_f241460e
```
✅ `input_tokens = 834` confirms real Bedrock call, not mock.

### Criterion 4 — Blank PDF → 422 (not 500)

```
HTTP 422  {"detail":"No /Root object! - Is this really a PDF?"}
```
✅ ParseError surfaced as readable 422 detail string; no traceback.

### Criterion 5 — Wrong AWS key → 422 (not 500)

```
HTTP 422  {"detail":"An error occurred (UnrecognizedClientException) when calling the
           Converse operation: The security token included in the request is invalid."}
```
✅ BedrockError caught at endpoint layer → 422 with readable message; never 500.

---

## New DB Tables (Alembic 0002)

```sql
raw_documents   — filename, format, document_kind, raw_text, char_count, uploaded_at
extraction_runs — raw_document_id, model_id, prompt_version, prompt_text,
                  raw_llm_output, status, entity_id, errors[], warnings[],
                  input_tokens, output_tokens, latency_ms, created_at
```

Both tables are append-only observability records. Not FK'd from candidates/positions
so failed runs (no entity) still produce a log row.

---

## Key Design Decisions (interview-defensible)

**Why PARTIAL instead of reject?** A candidate with 9/10 fields correct is more
useful than no candidate. PARTIAL means "entity created, review warnings." FAILED
means "nothing persisted, safe to retry." The distinction is in the type system —
callers cannot confuse them.

**Why heuristics before LLM?** A regex on an email field is 100% accurate by
definition. LLMs hallucinate. Heuristics lock in first; the LLM fills semantic gaps.

**Why store the full rendered prompt in extraction_runs?** The prompt file may be
renamed or deleted. The DB row is immutable and self-contained. It also captures the
interpolated `raw_text` and `heuristic_hints` that the version slug alone can't
reconstruct.

**Why flush (not commit) inside the logger?** Raw documents and extraction runs are
part of the same logical transaction as the candidate insert. Flush assigns the
DB-generated `id` without releasing the transaction. The endpoint commits once —
either everything lands or nothing does.

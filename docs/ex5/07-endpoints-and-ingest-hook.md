# Segment 07 — Match Endpoints & Ingest Auto-Embed Hook

**Depends on:** 04 (service), 05 (search), 06 (explainer). **Blocks:** 08 (frontend).

## Purpose

Expose the two suggestion features over HTTP, and wire embedding generation into the ingest pipeline so new and
updated records embed automatically (drift-safe). Read-only → any authenticated user (incl. viewer), matching
the Ex4 chat endpoint.

## Public artifacts

### 1. Pydantic schemas (`api/app/schemas.py`, append; use `_CONFIG` at `schemas.py:13`)
```python
class CandidateMatch(BaseModel):        # position view → suggested candidates
    model_config = _CONFIG
    candidate_id: str
    full_name: str
    headline: str
    score: float

class PositionMatch(BaseModel):         # candidate view → recommended positions
    model_config = _CONFIG
    position_id: str
    title: str
    score: float
    explanation: str
```
`_CONFIG` serialises to camelCase (`candidateId`, `fullName`, …) so the frontend types are camelCase.

### 2. Router (`api/app/routers/matches.py`)
```python
@router.get("/positions/{position_id}/candidate-matches", response_model=list[CandidateMatch])
async def candidate_matches(position_id, db=Depends(get_db), _=Depends(get_current_user)):
    scored = await search_candidates_for_position(position_id, db)      # ≤3, excludes linked, ≥ threshold
    # eager-load the matched candidates to fill full_name/headline (one query, _EAGER not needed — scalar cols)
    # return [CandidateMatch(candidate_id=s.candidate_id, full_name=..., headline=..., score=s.score) ...]

@router.get("/candidates/{candidate_id}/position-matches", response_model=list[PositionMatch])
async def position_matches(candidate_id, db=Depends(get_db), _=Depends(get_current_user)):
    scored = await search_positions_for_candidate(candidate_id, db)     # ≤3, excludes applied, ≥ threshold
    # load matched positions; for each, explain_match(...) via asyncio.gather (≤3 short calls)
    # return [PositionMatch(position_id=..., title=..., score=..., explanation=...) ...]
```
- Empty `scored` → return `[]` (the candidate view suppresses the section; the position view shows an empty state).
- Load matched entity rows by id to populate `full_name`/`headline`/`title` so the frontend needs no extra fetch.
- Candidate view: fan out explanations with `asyncio.gather` to stay under 2s with ≤3 generations.
- Register in `api/app/main.py`: add `matches` to the import at `main.py:29` and
  `app.include_router(matches.router, prefix="/api")` alongside `main.py:31-36`.

### 3. Ingest auto-embed hook (`api/app/ingest/__init__.py`)
After a candidate is persisted (`persist_candidate` returns `entity_id` at `ingest/__init__.py:55`), re-load it
with children and call `upsert_candidate_embedding(candidate, db, client)` before the endpoint commits.
Symmetric after `persist_position` (`ingest/__init__.py:100`). This keeps vectors fresh on every ingest and,
via the sha guard, re-embeds only when the composed text actually changed (drift handling).
- Pass a `BedrockClient | None` through so tests inject the mock; default constructs a real client (mirrors how
  `bedrock_client` is threaded through `call_llm_for_cv`, `llm.py:113`).
- Failure to embed must **not** fail ingestion — wrap in try/except, log, continue (embeddings backfill can fix
  it later). Ingestion succeeding is the contract; the embedding is best-effort at ingest time.

## Reused utilities
- `search_candidates_for_position` / `search_positions_for_candidate` — segment 05.
- `explain_match` — segment 06.
- `upsert_candidate_embedding` / `upsert_position_embedding` — segment 04.
- `get_current_user` (read-only auth) — `api/app/auth.py`, imported as in `routers/candidates.py:8`.
- `_CONFIG` camelCase — `api/app/schemas.py:13`. Router registration — `api/app/main.py:29-36`.
- Persist-then-commit-once discipline; `entity_id` returns — `api/app/ingest/__init__.py:55,100`.
- Monkeypatch target: patch `app.embeddings.service.BedrockClient` / `app.ingest.BedrockClient` — the importing namespace.

## Tests (`api/tests/embeddings/test_matches_endpoint.py`) — test-first, mocks injected
1. `test_position_candidate_matches_excludes_linked` — GET returns ≤3, none already linked, scores present, descending.
2. `test_candidate_position_matches_have_explanations` — GET returns ≤3 with non-empty `explanation` (mock reply).
3. `test_threshold_empty_returns_empty_list` — high threshold (or no near vectors) → `[]` (200, empty).
4. `test_viewer_can_read` — a viewer token (read-only) gets 200 on both endpoints.
5. `test_ingest_creates_embedding` — ingesting a new CV (mock LLM + mock embed) creates its `candidate_embeddings` row.
6. `test_ingest_embed_failure_does_not_fail_ingest` — embed raises → ingest still returns success, no embedding row.
7. `test_camelcase_payload` — response keys are `candidateId`/`fullName`/`positionId`/`explanation`.

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_matches_endpoint.py` green; full suite green.
- Live: `GET /api/positions/{id}/candidate-matches` → 3 scored candidates (none linked);
  `GET /api/candidates/{id}/position-matches` → ≤3 positions each with a grounded explanation. Both < 2s.

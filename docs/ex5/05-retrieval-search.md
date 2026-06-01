# Segment 05 — Retrieval Search (cosine top-N + exclusion + threshold)

**Depends on:** 01 (tables), 02 (only indirectly), 04 (stored vectors exist). **Blocks:** 07 (endpoints).

## Purpose

The read path: given a position, return the top-N most similar candidates **not already linked**, above a
similarity threshold, with scores — and the symmetric candidate→positions search. The key design move is to
**reuse the entity's already-stored vector as the query** (no live embed), and to **separate the pure
ranking/threshold/exclusion logic from the dialect-specific distance query** so both are testable. The vector
distance is the only thing that differs between Postgres and SQLite; the ranking is shared.

## Public artifacts (`api/app/embeddings/search.py`)

```python
SIMILARITY_THRESHOLD = float(os.getenv("EMBED_SIM_THRESHOLD", "0.5"))  # cosine; score = 1 - distance

@dataclass
class ScoredCandidate: candidate_id: str; score: float
@dataclass
class ScoredPosition:  position_id: str;  score: float

# --- pure logic (no DB; fully unit-testable on any platform) ---
def cosine(a: list[float], b: list[float]) -> float: ...   # dot / (||a||·||b||); inputs may be unit-norm already
def rank_top_n(scored: list[tuple[str, float]], exclude: set[str],
               threshold: float, n: int) -> list[tuple[str, float]]:
    """Drop ids in `exclude`, drop score < threshold, sort by score desc, take n."""

# --- service functions (wire query vector + distance source + rank) ---
async def search_candidates_for_position(position_id: str, db: AsyncSession, *,
        top_n: int = 3, threshold: float = SIMILARITY_THRESHOLD) -> list[ScoredCandidate]: ...
async def search_positions_for_candidate(candidate_id: str, db: AsyncSession, *,
        top_n: int = 3, threshold: float = SIMILARITY_THRESHOLD) -> list[ScoredPosition]: ...
```

### `search_candidates_for_position` flow
1. Load `position_embeddings.embedding` for `position_id` (the **query vector** — already stored). If absent →
   return `[]` (not yet embedded).
2. `exclude = {candidate_id for (…) in applications where position_id == :pid}` — the already-linked set.
3. Dialect-branch the distance query (copy the seam at `chat/executor.py:25-46`):
   - **Postgres:** one SQL query ranks + excludes + limits in the DB:
     ```sql
     SELECT candidate_id, 1 - (embedding <=> :qvec) AS score
     FROM candidate_embeddings
     WHERE candidate_id NOT IN (SELECT candidate_id FROM applications WHERE position_id = :pid)
     ORDER BY embedding <=> :qvec
     LIMIT :k
     ```
     Pass `:qvec` as a bound param (the pgvector SQLAlchemy type binds the list; or cast `:qvec::vector`).
     Use the isolated async engine `from app.db import engine` (the executor's `_async_engine` import,
     `executor.py:10`) — `AsyncSession.get_bind()` returns a *sync* engine, so don't derive it from the session.
   - **SQLite (tests):** ORM-load all `candidate_embeddings` rows, compute `cosine(qvec, row.embedding)` in
     Python (the stored value is a JSON list), then `rank_top_n` with the exclude set + threshold.
4. Apply `rank_top_n` (it's already applied in SQL on Postgres, but still run threshold filtering uniformly so
   both paths return the same shape) → `list[ScoredCandidate]`.

`search_positions_for_candidate` is symmetric: query vector = `candidate_embeddings.embedding`; exclude =
positions the candidate already applied to; rank `position_embeddings`.

## Why this shape
- **Performance / 2s NFR:** no LLM and no live embed in the hot path — a single bounded query. Sub-second.
- **Reproducibility:** the query vector is the stored one; identical inputs → identical ranking.
- **Extensibility seam:** the `WHERE … NOT IN (…)` is where future relational filters (seniority, department,
  availability) bolt on — vector search AND a relational predicate, one query. Note this in a comment.
- **Testability:** `rank_top_n`/`cosine` are pure → exhaustively unit-tested; the SQLite path exercises the
  *same* ranking code, only the distance source differs (exactly the Ex4 executor philosophy).

## Reused utilities
- Dialect-branch seam + isolated engine — `api/app/chat/executor.py:10,25-46`.
- Applications join for exclusion — `Application` model `api/app/models.py:300` (UniqueConstraint `:324`).
- `SIMILARITY_THRESHOLD` env pattern — mirrors `BEDROCK_MODEL_ID` env default (`ingest/llm.py:15`).

## Tests (`api/tests/embeddings/test_search.py`) — test-first
Seed + `backfill_all` with `MockEmbeddingClient` in the fixture so every row has a deterministic vector.
1. `test_rank_top_n_pure` — excludes ids in the set, drops sub-threshold, sorts desc, caps at n (no DB).
2. `test_cosine_basic` — cosine(v, v) ≈ 1.0; cosine of orthogonal ≈ 0.
3. `test_candidates_for_position_excludes_linked` — for a position with 2 linked candidates, neither appears
   in the results; results ⊆ unlinked candidates.
4. `test_threshold_suppresses` — with `threshold=0.99` (mock vectors rarely that close), returns `[]`.
5. `test_top_n_cap` — never more than `top_n` results; ordered by score desc.
6. `test_positions_for_candidate_symmetry` — excludes already-applied positions; returns scored positions.
7. `test_no_stored_vector_returns_empty` — querying an entity with no embedding row → `[]`.

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_search.py` green.
- Live (Postgres + backfill done): call `search_candidates_for_position("job_xxx")` in a REPL → 3 scored
  candidates, none already linked, scores descending and ≥ 0.5. Confirm < 2s.

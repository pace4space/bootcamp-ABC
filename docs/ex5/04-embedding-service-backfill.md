# Segment 04 — Embedding Service & Backfill

**Depends on:** 02 (text builders), 03 (`embed`). **Blocks:** 05 (needs stored vectors), 07 (ingest hook).

## Purpose

The write path: build the standardized text, hash it, embed it **only if it changed**, and upsert the
`*_embeddings` row with the vector + text + model + sha + `updated_at`. Plus an **idempotent** backfill that
embeds every existing candidate and position and logs counts + token cost. Idempotency + the sha guard are
what make re-ingest cheap and reproducible (Principles 1 & 3).

## Public artifacts (`api/app/embeddings/service.py`)

```python
@dataclass
class BackfillReport:
    candidates_embedded: int
    positions_embedded: int
    skipped: int
    total_tokens: int

async def upsert_candidate_embedding(candidate, db: AsyncSession,
                                     client: BedrockClient | None = None) -> bool:
    """Build text -> sha. If an embedding row exists with the same sha, skip (return False).
    Otherwise embed, upsert the row (vector, embedding_text, embedding_model, sha,
    updated_at=datetime.now(UTC)), flush. Return True if (re)embedded."""

async def upsert_position_embedding(position, db, client=None) -> bool: ...   # symmetric

async def backfill_all(db: AsyncSession, client: BedrockClient | None = None) -> BackfillReport:
    """Embed all candidates + positions via the upsert fns; accumulate counts + tokens; log per record."""
```

### Upsert logic (both entities)
1. `text = build_candidate_text(candidate)` (segment 02).
2. `sha = text_sha256(text)`.
3. Load any existing embedding row by PK. If `row.text_sha256 == sha` → **skip**, return `False`
   (no Bedrock call — this is the cost + reproducibility guard, and the drift check).
4. Else `vec, tokens = client.embed_with_usage(text)` run via `loop.run_in_executor` (don't block the loop).
5. Upsert: insert or update `embedding`, `embedding_text`, `embedding_model=client.embed_model_id`,
   `text_sha256=sha`, `updated_at=datetime.now(timezone.utc)`. `flush()` — the caller commits.
6. **Log** (Principle 3): `logger.info("embedded %s len(text)=%d tokens=%d", id, len(text), tokens)`.
   Log the id + text length + tokens; the full `embedding_text` is stored in the row for inspection.

### Backfill entry point (`docs/ex5/backfill.py`)
A standalone async script (outputs/scripts belong in `docs/ex5/`, not `/tmp`) that:
- builds an `AsyncSession` from `app.db` (use `AsyncSessionLocal`), constructs a real `BedrockClient`,
- eager-loads all candidates/positions with their children (the `_EAGER` pattern, `routers/candidates.py:32`),
- calls `backfill_all`, commits once, prints the `BackfillReport` (embedded / skipped / total_tokens → cost).
- Idempotent: a second run skips everything (all shas match). Safe to re-run after any profile edit.

## Reused utilities
- `build_candidate_text` / `build_position_text` / `text_sha256` — segment 02 (`embeddings/text_builder.py`).
- `BedrockClient.embed_with_usage` — segment 03 (`api/app/ingest/llm.py`).
- Eager-load options `_EAGER` — `api/app/routers/candidates.py:32`.
- `flush()`-then-caller-commits discipline — `api/app/ingest/persister.py`.
- `AsyncSessionLocal` — `api/app/db.py:53`.
- `run_in_executor` for the sync client — `api/app/ingest/llm.py:91-96`.

## Tests (`api/tests/embeddings/test_service.py`) — test-first, `MockEmbeddingClient`
1. `test_backfill_embeds_all` — on the seeded DB, `backfill_all` creates an embedding row for every candidate
   and position; report counts match the seed counts; `total_tokens > 0`.
2. `test_backfill_idempotent` — second `backfill_all` run embeds 0, `skipped == total` (all shas match).
3. `test_reembed_on_text_change` — mutate a candidate's `summary`, re-run upsert → returns `True`, exactly one
   row's `updated_at`/`text_sha256` changed; others untouched.
4. `test_embedding_text_stored_matches_builder` — the stored `embedding_text` equals `build_candidate_text(c)`
   (inspectability / drift contract).
5. `test_skip_returns_false` — calling `upsert_candidate_embedding` twice with no change → second returns `False`,
   no new Bedrock call (assert mock call count).

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_service.py` green.
- Live: `docker compose up -d` (pgvector image) → `alembic upgrade head` →
  `python docs/ex5/backfill.py` → prints e.g. `embedded 9 candidates, 6 positions, skipped 0, tokens 4123`;
  a second run prints `skipped 15` — proves idempotency.

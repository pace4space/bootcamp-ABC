# Segment 10 — Hybrid Search (OPTIONAL stretch)

> **OPTIONAL.** Build this only if segments 01–09 land with schedule to spare. Ex5 is "done" without it.
> This is the Ex5 analog of how Ex4 handled Claude-on-Bedrock: designed and documented, not a required deliverable.

**Depends on:** 05 (search), 07 (endpoints/wiring). Touches the Ex4 chat loop (`api/app/chat/`).

## Purpose

Let the Ex4 chat answer "find candidates like X but only Active" / "similar positions in Platform dept" by
combining **semantic retrieval** with **relational filters** — vector search AND a `WHERE` clause. This is the
payoff of the extensibility seam noted in segment 05 (the exclusion join is where filters bolt on).

## Shape (`api/app/embeddings/hybrid.py`)

```python
async def hybrid_candidate_search(query_text: str, db: AsyncSession, *,
        filters: dict | None = None, top_n: int = 5,
        client: BedrockClient | None = None) -> list[ScoredCandidate]:
    """Embed query_text (live embed — this is a free-text query, not a stored entity),
    rank candidate_embeddings by cosine, AND apply relational filters
    (status='Active', city=..., seniority via positions, etc.) in the same query."""
```

- Unlike segments 05's entity-to-entity search, the **query is free text** → this is the one place we call
  `client.embed(query_text)` live (segment 03). Everything else (dialect branch, `rank_top_n`, threshold) is
  reused from segment 05 — do not reinvent.
- `filters` map to SQL predicates joined onto the candidate/position table (the seniority/department/availability
  extensibility hook). Keep them an allowlist (column → operator) so this stays injection-safe, consistent with
  the Ex4 guard philosophy (`api/app/chat/guard.py`).

## Wiring into the chat loop
Two viable integrations — pick the lighter one:
- **A (recommended):** add a retrieval branch in `run_chat_query` (`api/app/chat/__init__.py`) that, for
  "find similar …" intents, calls `hybrid_*_search` instead of `generate_sql`, then hands the rows to the
  existing `synthesize_answer` (`chat/answerer.py`) — the answer path is unchanged, only the retrieval source differs.
- **B:** a separate `POST /api/chat/semantic` endpoint. More surface; only if you want to keep the two paths fully separate.

Intent routing can be a simple heuristic ("similar"/"like"/"resembles" → semantic) — do NOT over-engineer a classifier.

## Reused utilities
- `search.py` `cosine` / `rank_top_n` / dialect branch — segment 05.
- `BedrockClient.embed` — segment 03.
- `synthesize_answer` — `api/app/chat/answerer.py` (Ex4).
- Guard/allowlist discipline — `api/app/chat/guard.py` (Ex4).

## Tests (`api/tests/embeddings/test_hybrid.py`)
1. `test_hybrid_applies_filter` — `filters={"status":"Active"}` excludes Archived candidates from results.
2. `test_hybrid_ranks_by_query` — a query embedding nearer to one candidate's text ranks it first (mock embed).
3. `test_filter_allowlist_rejects_unknown_column` — an unknown filter key is rejected (no raw SQL injection).

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_hybrid.py` green.
- Live (if wired into chat): "find candidates similar to a senior DevOps role, only Active" → semantically
  ranked, Active-only, grounded answer. Note it in `docs/ex5/retrieval-eval.md` as the hybrid example.

# Ex5 — Exercise Overview & Architecture (Semantic Search)

> **For the Sonnet BUILD session.** These segment files (`00`–`09`, plus optional `10`) are the
> handoff contract. Each is self-contained: exact signatures, reused utilities with `file:line`
> pointers, test names + assertions, and its dependency on prior segments. Implement **test-first**,
> in numeric order. Commit per segment. Do not start a segment before its stated dependencies are green.

## Purpose

Ex5 adds **semantic search** to Hellio HR: candidates and positions match by *meaning*, not keyword
overlap. A candidate whose CV says "EKS experience" should surface for a position requiring
"Kubernetes skills," even with zero shared tokens. This is the first **vector retrieval** feature —
it complements (does not replace) the Ex4 SQL-RAG chat.

Two user-facing features ship:
1. **Position view → "Suggested candidates":** top 3 candidates ranked by semantic similarity,
   **excluding candidates already linked** to that position, each with a similarity score.
2. **Candidate view → "Recommended positions":** up to top 3 positions ranked by relevance, each with
   an **LLM-generated, grounded explanation**; show fewer than 3 (or none) when fewer are genuinely relevant.

Plus a **retrieval-evaluation** deliverable: a TSV export loaded into the TensorFlow Embedding
Projector (UMAP) to validate clustering, and a markdown write-up comparing semantic vs SQL-keyword search.

## The embed → store → retrieve → explain loop

```
INGEST / BACKFILL (write path)
  candidate/position row
        │
        ▼
  embeddings/text_builder.py  → standardized "embedding_text"   [summary+skills+experience | desc+requirements]
        │
        ▼
  ingest/llm.py BedrockClient.embed()  → Titan v2 512-dim vector  [invoke_model, normalize=true]
        │
        ▼
  embeddings/service.py  → upsert candidate_embeddings / position_embeddings  [text+sha+model+updated_at]

RETRIEVE (read path, per page view)
  position_id / candidate_id
        │
        ▼
  embeddings/search.py  → reuse the entity's STORED vector as the query   [no live embed → fast, reproducible]
        │
        ▼
  pgvector cosine top-N  (Postgres <=> operator | SQLite pure-Python)  + SQL exclusion of already-linked
        │
        ▼
  rank_top_n(scored, exclude, threshold, n)  → list[ScoredCandidate | ScoredPosition]
        │
        ▼ (candidate view only)
  embeddings/explainer.py  → BedrockClient.converse grounds a 1–2 sentence "why it fits"
        │
        ▼
  GET /api/positions/{id}/candidate-matches   (scores only)
  GET /api/candidates/{id}/position-matches   (scores + explanations)
```

## Three principles (the lessons of this exercise)

1. **Reproducibility over magic.** Same input text → same vector. This requires (a) **deterministic
   `embedding_text` builders** (stable field order, child rows ordered by `sort_order`) and (b) pinned
   model params (`dimensions:512`, `normalize:true`). A `text_sha256` digest makes drift observable and
   backfill idempotent. The embedding model is a **black box** — input text quality is the only lever.
2. **Grounding over invention** (inherited from Ex4's answerer). The match **explanation** may cite only
   the candidate's actual skills/experience and the position's actual requirements that were fed to it;
   when no concrete overlap exists it must say the match is weak — never invent a skill, employer, or requirement.
3. **Observability of *what was embedded and why*.** Store the exact `embedding_text` and `embedding_model`
   alongside every vector; log embedding counts + token cost on backfill. A retrieval you cannot inspect
   is not debuggable — and here the bug is almost always in the composed text, not the threshold.

A fourth, quieter principle: **the threshold is a filter, not a truth.** Cosine scores are *relative
rankings*, not absolute percentages. Filter weak matches (default `0.5`); never over-interpret a single number.

## What we have entering Ex5

- Running FastAPI + Postgres backend (Ex2); document-derived candidate/position rows + `summary`/`description` (Ex3).
- `BedrockClient` (text generation only) — `converse()`/`converse_messages()` at `api/app/ingest/llm.py:33`.
- The Ex4 SQL-RAG chat: `api/app/chat/` (generator, guard, executor, answerer, `run_chat_query`).
- The **dialect-branch seam** — `api/app/chat/executor.py:25-46` (`bind.dialect.name`; Postgres vs SQLite paths).
- The isolated async engine — `from app.db import engine` (`api/app/db.py:40`), imported as `_async_engine` in the executor.
- Versioned-prompt loader + fence stripper — `api/app/text_utils.py:8,16`.
- Seeded SQLite test DB with Active+Archived candidates, Open+Closed positions, skills, experience,
  requirements, applications (`api/tests/conftest.py`); `MockBedrockClient` pattern; ARRAY→JSON patch at `conftest.py:45-48`.

## What we produce

- A new backend module `api/app/embeddings/` (sibling to `ingest/` and `chat/`): `text_builder.py`,
  `service.py`, `search.py`, `explainer.py`, `prompts/explain-v1.txt`.
- Two new DB tables: `candidate_embeddings`, `position_embeddings` (Alembic `0004`, pgvector).
- An additive `BedrockClient.embed()` (Titan v2, `invoke_model`) — existing `converse` tests untouched.
- Two read-only endpoints: `GET /api/positions/{id}/candidate-matches`, `GET /api/candidates/{id}/position-matches`.
- An ingest auto-embed hook so new/updated records embed on the way in (drift-safe).
- A one-time backfill script (`docs/ex5/backfill.py`) and a TSV export (`docs/ex5/export_embeddings.py`).
- `docs/ex5/retrieval-eval.md`: Projector/UMAP checklist + semantic-vs-SQL comparison.
- Suggestion sections in `PositionDetail.tsx` and `CandidateProfile.tsx`.
- Full automated test coverage with Bedrock/embeddings mocked; a manual live-Titan demo + the validation checklist.

## Module learning map

| Segment | Module | Core lesson |
|---------|--------|-------------|
| 01 | embedding tables + `0004` migration + pgvector | A Postgres-only column type that stays SQLite-portable via `with_variant(JSON)` — the seam, isolated to new tables |
| 02 | `text_builder.py` | The composed text **is** the model's input quality — deterministic, standardized, low-fluff; the #1 design lever |
| 03 | `BedrockClient.embed` | Titan is a *different* Bedrock API (`invoke_model`, not `converse`); validate the 512-dim contract; mock deterministically |
| 04 | `service.py` + backfill | Embed once, skip-if-unchanged (sha); backfill is idempotent; log what was embedded + cost |
| 05 | `search.py` | Vector distance is dialect-specific; ranking/threshold/exclusion is pure logic — separate them so both are testable |
| 06 | `explainer.py` | Grounding = cite only the retrieved fields; flag weak matches instead of inventing overlap |
| 07 | `routers/matches.py` + ingest hook | Combine vector search with a relational exclusion filter in one query; auto-embed on ingest keeps vectors fresh |
| 08 | `PositionDetail.tsx` + `CandidateProfile.tsx` | Surface scores + explanations; suppress the section when nothing clears the threshold |
| 09 | export + eval | Validate embedding quality *visually* (Projector/UMAP) before trusting retrieval; articulate semantic vs keyword |
| 10 *(optional)* | `hybrid.py` | Vector retrieval + relational filters bolted onto the Ex4 chat loop |

## Locked decisions (do not relitigate)

1. **Two dedicated 1:1 embedding tables** (`candidate_embeddings`, `position_embeddings`), FK `ON DELETE
   CASCADE` — core entity tables and the 100+ existing tests stay untouched; the vector type's SQLite seam
   is isolated. (Chosen over columns-on-main-tables and a single polymorphic table.)
2. **Amazon Titan `amazon.titan-embed-text-v2:0`, 512-dim, `normalize:true`**, via boto3 `invoke_model`,
   added additively to `BedrockClient`. Env override `BEDROCK_EMBED_MODEL_ID`.
3. **No ANN index** at this data scale (tens of rows) — exact sequential cosine is sub-millisecond and
   reproducible. HNSW (`vector_cosine_ops`) documented as future hardening past ~10k rows.
4. **Reuse the stored entity vector as the query** at retrieval time (no live embed on page load) — keeps
   both endpoints well under the 2s NFR and fully reproducible.
5. **Threshold default `0.5`** (cosine; score = 1 − distance) as a named constant + env override; calibrated
   against the Projector/UMAP pass, not guessed.
6. **Explanations are candidate-view only** and lazy (≤3 short `converse` calls); the position view returns
   scores only — cheap by construction.

## Carry-forward

- **Ex6 (HR agent):** `search_*` and `explain_match` are callable functions; the agent invokes them like the
  endpoints do — same shape as `run_chat_query()` (Ex4) and `run_cv_pipeline()` (Ex3).
- **Reporting:** embedding token counts mirror `extraction_runs`/`query_runs` cost data; a future dashboard reads them.
- **Extensibility:** the relational-exclusion join in `search.py` is the seam where later filters (seniority,
  department, availability) bolt on — vector search AND a `WHERE` clause, one query.

## Conventions inherited from Ex2/Ex3/Ex4 (apply throughout)

- Async SQLAlchemy 2.x; `AsyncSession` via `Depends(get_db)` (`api/app/db.py:64`).
- Pydantic camelCase via `_CONFIG` (`alias_generator=to_camel`) — `api/app/schemas.py:13`.
- Persist via `flush()` inside the request; the **endpoint** calls `db.commit()` once.
- SQLite tests: supply explicit `datetime.now(timezone.utc)` at write time — never rely on
  `server_default="now()"` (Postgres syntax SQLite can't read).
- Monkeypatch the name in the namespace that **imported** it (e.g. `app.embeddings.service.BedrockClient`),
  not the definition site. See segment 03/07.
- New ORM models **must** be added to the `from app.models import (...)` block in `conftest.py:25` or their
  tables won't be created by `create_all` (the QueryRun lesson, Ex4).

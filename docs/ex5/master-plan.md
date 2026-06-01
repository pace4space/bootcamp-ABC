# Ex5 — Semantic Candidate/Position Search (Master Plan)

## Context

Hellio HR has a stable UI contract (Ex1), a FastAPI + Postgres backend (Ex2), an LLM ingestion pipeline that
produces structured rows + `summary`/`description` (Ex3), and an SQL-RAG chat that answers questions by
translating intent into read-only SQL (Ex4). Ex5 adds the first **vector retrieval** feature: candidates and
positions match by *meaning* (an "EKS experience" candidate surfaces for a "Kubernetes skills" position), not
keyword overlap.

The core is an **embed → store → retrieve → explain** loop on top of pgvector:

```
WRITE:  row → text_builder (standardized embedding_text) → BedrockClient.embed (Titan 512-dim)
            → service.upsert → candidate_embeddings / position_embeddings
READ:   id  → reuse stored vector as query → pgvector cosine top-N (Postgres <=>) | SQLite python-cosine
            → rank_top_n(exclude already-linked, threshold) → [scored]
            → (candidate view only) explainer grounds a 1–2 sentence "why it fits"
            → GET /api/positions/{id}/candidate-matches | /api/candidates/{id}/position-matches
```

**Why a staged module, not a script:** identical rationale to Ex3's `ingest/` and Ex4's `chat/` — Ex6's HR
agent will call `search_*`/`explain_match` the same way the endpoints do. Typed boundaries keep each stage
independently testable, and the SQLite-vs-pgvector seam is contained to two new tables + one search module.

### Locked decisions (confirmed with user)
1. **Two dedicated 1:1 embedding tables** (`candidate_embeddings`, `position_embeddings`), FK `ON DELETE
   CASCADE` — core entity tables + the 100+ existing tests stay untouched; the Postgres-only `vector` type and
   its SQLite JSON-variant seam are isolated. (Over columns-on-main-tables and a single polymorphic table.)
2. **Amazon Titan `amazon.titan-embed-text-v2:0`, 512-dim, `normalize:true`** via boto3 `invoke_model`, added
   *additively* to `BedrockClient` so Ex3/Ex4 `converse` tests are untouched. Env override `BEDROCK_EMBED_MODEL_ID`.
3. **No ANN index** at this data scale — exact sequential cosine is sub-ms and reproducible; HNSW
   (`vector_cosine_ops`) documented as future hardening past ~10k rows.
4. **Reuse the stored entity vector as the query** at retrieval time (no live embed on page load) → both
   endpoints well under the 2s NFR, fully reproducible.
5. **Threshold default `0.5`** (cosine; score = 1 − distance) as a named constant + env override, calibrated
   against the Projector/UMAP pass.
6. **Hybrid search is an optional stretch segment** (`10`), not a required deliverable.
7. **Branch base:** `ex5` is cut off **`ex4`** (not master) — master is still pre-Ex4 and lacks the `chat/`
   module that Ex5 extends.

---

## Deliverable shape

The user wants the plan **divided into segmented `.md` files we can delegate to Sonnet**, mirroring
`docs/ex3/` and `docs/ex4/` (00-overview + numbered modules + master-plan). Execution has two layers:

1. **Write `docs/ex5/*.md`** — self-contained, test-first segment plans (the delegation units). ← THIS session.
2. **Delegate each segment to Sonnet** for implementation, in dependency order, committing per segment.

### Segmented plans authored (`docs/ex5/`)

| File | Scope | Delegable unit |
|------|-------|----------------|
| `00-overview.md` | Purpose, the embed→store→retrieve→explain loop, 3 principles (reproducibility / grounding / observability), module map, locked decisions, carry-forward to Ex6 | — |
| `01-storage-and-migration.md` | `Vector(512).with_variant(JSON,"sqlite")`; `CandidateEmbedding`/`PositionEmbedding`; Alembic `0004` (CREATE EXTENSION guarded, 2 tables, no ANN index); docker-compose → `pgvector/pgvector:pg16`; `requirements.txt += pgvector`; register models in conftest | Sonnet |
| `02-embedding-text-builders.md` | pure deterministic `build_candidate_text`/`build_position_text`/`text_sha256` — the #1 design lever | Sonnet |
| `03-embedding-client.md` | additive Titan `embed`/`embed_with_usage`/`embed_batch` on `BedrockClient` (`invoke_model`, 512-dim validate); deterministic `MockEmbeddingClient` | Sonnet |
| `04-embedding-service-backfill.md` | `service.py` upsert (build→sha→skip-if-unchanged→embed→upsert) + idempotent `backfill_all` + `docs/ex5/backfill.py`; logs text+counts+tokens | Sonnet |
| `05-retrieval-search.md` | `search.py` pure `cosine`/`rank_top_n` + dialect-branched query; reuse stored vector; SQL exclusion of already-linked; threshold | Sonnet |
| `06-explainer.md` | `explainer.py` + `prompts/explain-v1.txt` — grounded, anti-hallucination "why it fits" | Sonnet |
| `07-endpoints-and-ingest-hook.md` | `routers/matches.py` 2 GET endpoints + `CandidateMatch`/`PositionMatch` schemas; register in main; ingest auto-embed hook (drift-safe, best-effort) | Sonnet |
| `08-frontend.md` | `types.ts` + `db.ts` match fns; "Suggested candidates" in PositionDetail; "Recommended positions" in CandidateProfile; reuse card/badge/heading; suppression | Sonnet |
| `09-evaluation.md` | `export_embeddings.py` (TSV) + `retrieval-eval.md` (Projector/UMAP checklist + semantic-vs-SQL + validation checklist) | Sonnet |
| `10-hybrid-search.md` *(optional)* | `hybrid.py` — semantic + relational filters bolted onto the Ex4 chat loop | Sonnet (if time) |

---

## Architecture detail

### New backend module: `api/app/embeddings/` (sibling to `ingest/`, `chat/`)
```
api/app/embeddings/
  __init__.py
  text_builder.py   build_candidate_text / build_position_text / text_sha256   (pure)
  service.py        upsert_candidate_embedding / upsert_position_embedding / backfill_all
  search.py         cosine / rank_top_n (pure) + search_candidates_for_position / search_positions_for_candidate
  explainer.py      explain_match(candidate, position, score, client) -> (text, in_tok, out_tok)
  prompts/
    explain-v1.txt  [SYSTEM] grounding/anti-hallucination rules   [USER] {candidate_json}\n{position_json}
```

### Reused utilities (do not reinvent)
- `BedrockClient` + `converse()` — `api/app/ingest/llm.py:33,42`. **Additive `embed()`** (Titan `invoke_model`,
  NOT `converse`); keep `converse`/`converse_messages` signatures untouched so Ex3/Ex4 tests are unchanged.
- Dialect-branch seam (`bind.dialect.name`, Postgres vs SQLite) + isolated engine
  (`from app.db import engine`) — `api/app/chat/executor.py:10,25-46`. The vector search copies this shape.
- `load_prompt(prompts_dir, version)` + `strip_fences` — `api/app/text_utils.py:16,8`.
- `get_current_user` (read-only → any authenticated user incl. viewer) — `api/app/auth.py` (import as in
  `routers/candidates.py:8`).
- Eager-load `_EAGER` + `_to_schema` — `api/app/routers/candidates.py:32,41`.
- Pydantic camelCase `_CONFIG` (`alias_generator=to_camel`) — `api/app/schemas.py:13`.
- Frontend seam `apiFetch(path, token, init)` — `src/lib/db.ts:9`.
- `QueryRun` model style (scalar cols, SQLite-portable, explicit `datetime.now(UTC)`) — `api/app/models.py:419`.
- ARRAY→JSON conftest precedent (why `with_variant` works) — `api/tests/conftest.py:45-48`; model import block `:25`.
- Test fixtures `client`, `auth_headers`, `viewer_headers`, seeded DB, `MockBedrockClient` — `api/tests/conftest.py`,
  `api/tests/ingest/test_llm.py`.

### Critical files to create / modify
**Create:** `docs/ex5/00..10*.md` + `master-plan.md`; `api/app/embeddings/{__init__,text_builder,service,search,explainer}.py`;
`api/app/embeddings/prompts/explain-v1.txt`; `api/app/routers/matches.py`;
`api/alembic/versions/0004_embeddings.py`;
`api/tests/embeddings/{conftest,test_models,test_text_builder,test_embedding_client,test_service,test_search,test_explainer,test_matches_endpoint}.py`
(+ optional `test_hybrid.py`); `docs/ex5/{backfill.py,export_embeddings.py,retrieval-eval.md}`.
**Modify:** `api/app/models.py` (+2 embedding models, `EmbeddingType` variant); `api/app/ingest/llm.py` (+Titan
`embed`); `api/app/ingest/__init__.py` (auto-embed hook after `:55` and `:100`); `api/app/schemas.py` (+match
schemas); `api/app/main.py` (register `matches.router`, `:29-36`); `api/tests/conftest.py` (register models);
`docker-compose.yml` (pgvector image); `api/requirements.txt` (+pgvector); `src/lib/types.ts`; `src/lib/db.ts`;
`src/pages/PositionDetail.tsx`; `src/pages/CandidateProfile.tsx`.

### The seam that drives everything: SQLite vs pgvector
- Column type: `Vector(512).with_variant(JSON(), "sqlite")` → `create_all` builds JSON under SQLite, `vector`
  under Postgres; both round-trip `list[float]`. No new conftest patch.
- Every DB-touching vector op dialect-branches like `executor.py`: Postgres `embedding <=> :qvec`; SQLite loads
  rows and computes `cosine` in Python. The `rank_top_n`/threshold/exclusion logic is shared (pure) so tests
  cover it on both paths.

### Resilience / NFRs
- **<2s retrieval:** no LLM and no live embed in the hot path; one bounded query. Explanations are ≤3 short
  lazy `converse` calls (candidate view only), fanned out with `asyncio.gather`.
- **Reproducibility:** deterministic builders + pinned model params + sha guard.
- **Drift:** ingest auto-embed re-embeds only when the composed text's sha changes; embed failure is best-effort
  (never fails ingestion); backfill is idempotent.
- **Cost awareness:** `embed_with_usage`/`embed_batch` surface token counts; backfill logs a single summary.

---

## Verification

**Per-segment (automated, Bedrock/embeddings mocked):**
- `cd api && .venv/bin/pytest -q` — all existing tests stay green + new `tests/embeddings/` green.
- Segment 01 is the gate: the full suite must stay green after adding the variant column (proves the SQLite seam).
- Segment 05: `rank_top_n` excludes linked + drops sub-threshold + caps at n; SQLite end-to-end excludes the
  right candidates; high threshold → empty.
- Segment 07: endpoints exclude linked/applied, viewer can read, candidate view returns non-empty explanations
  (mock); ingest creates an embedding row; embed failure doesn't fail ingest.

**End-to-end (manual, live Titan — Ex3 Step 9 / Ex4 demo style):** `docker compose up` (pgvector image) →
`alembic upgrade head` → `python docs/ex5/backfill.py` (embeds all, idempotent on re-run) →
`python docs/ex5/export_embeddings.py` → load TSVs into the TensorFlow Projector (UMAP) → confirm clustering.
Then in the UI: a position shows top-3 unlinked candidates with scores; a candidate shows ≤3 positions with
grounded explanations and suppresses when none qualify. Record results + the validation checklist in
`docs/ex5/retrieval-eval.md`.

**UI:** `npm run dev` (Node 22 path); `tsc -b` + `npm run build` clean; screenshots → `docs/ex5/demo/`.

---

## Build handoff (confirmed with user): clean PLAN/BUILD split

```
Opus (THIS session):  branch ex5 off ex4  ->  write docs/ex5/*.md + master-plan  ->  commit  ->  STOP
You:                  open a NEW session on Sonnet, pointed at docs/ex5
Sonnet (BUILD):       read docs/ex5/00..09 (+10 optional)  ->  implement + test each segment  ->  commit per segment
```

The `docs/ex5/*.md` files ARE the handoff contract: each segment states the exact public signatures, the reused
utilities with `file:line` pointers, the test cases (names + assertions), and its dependency on prior segments.
A fresh Sonnet session must implement test-first with no further Opus input. Opus cost = planning only.

### This session's execution sequence (Opus)
1. `git checkout -b ex5` off `ex4`. ✅
2. Author `docs/ex5/00..10*.md` + this `master-plan.md`.
3. `git add docs/ex5 && git commit` (segment plans only — **no source code written this session**).
4. Stop. Report the branch + files + the exact Sonnet BUILD kickoff prompt.

### Recommended BUILD commit sequence
```
feat(ex5-01): embedding storage tables + pgvector migration + sqlite variant — N/N tests
feat(ex5-02): candidate/position embedding_text builders + sha — N/N tests
feat(ex5-03): BedrockClient.embed (Titan invoke_model, 512-dim) + mock — N/N tests
feat(ex5-04): embedding upsert service + idempotent backfill — N/N tests
feat(ex5-05): pgvector cosine retrieval + exclusion + threshold — N/N tests
feat(ex5-06): grounded match explanation generator (explain-v1) — N/N tests
feat(ex5-07): match endpoints + schemas + ingest auto-embed hook — N/N tests
feat(ex5-08): suggested candidates / recommended positions UI
feat(ex5-09): embedding TSV export + retrieval-eval (semantic vs SQL)
feat(ex5-10): OPTIONAL hybrid search (semantic + relational filters)   # if time
docs(ex5): retrieval-eval results + Projector/UMAP checklist
SUBMIT: Ex5 — semantic candidate/position search via Titan embeddings + pgvector
```

## Workflow notes
- **Commit every working step** (per CLAUDE.md); each BUILD commit leaves the app demo-able.
- **JOURNAL.md** entry per commit; **PROGRESS.md** Ex5 section — written during BUILD by Sonnet.
- **Model routing:** this planning + segment authoring = Opus; module implementation + test design = Sonnet
  (fresh session). Honors Opus-plans / Sonnet-builds.
- **post-commit hook** logs to `.skilllog`; run `/memory-synthesize` at the 5-commit cadence (BUILD).
- **Feedback to honor:** AsyncEngine for isolated PG connections (`from app.db import engine`); SQL structure
  validation (hybrid filter allowlist); LLM markdown-fence strip on the explainer; script outputs in `docs/ex5/`,
  not `/tmp`; Node 22 path for npm.

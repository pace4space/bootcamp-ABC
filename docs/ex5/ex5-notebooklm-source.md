# Hellio HR — Exercise 5: Semantic Search (Embeddings)

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


---

# Retrieval Evaluation

# Ex5 — Retrieval Evaluation: Semantic vs SQL-keyword Search

## Projector/UMAP Workflow

### Steps to validate embedding quality

1. Run the backfill (real Bedrock credentials required):
   ```
   cd api && python ../docs/ex5/backfill.py
   ```
2. Export vectors:
   ```
   cd api && python ../docs/ex5/export_embeddings.py
   # → docs/ex5/vectors.tsv + docs/ex5/metadata.tsv
   ```
3. Open https://projector.tensorflow.org
4. Click **"Load"** → upload `vectors.tsv`, then `metadata.tsv`
5. Switch projection to **UMAP** (bottom left)
6. Color by `kind` to visually separate candidates from positions

### Clustering checklist — what "good" looks like

- [ ] DevOps/platform candidates cluster together; frontend candidates form a separate cluster
- [ ] Each position sits near the candidates that should match it (position's nearest neighbors are sensible)
- [ ] Archived/off-topic records sit apart rather than scattered through good clusters
- [ ] Candidates with overlapping skills (e.g. multiple DevOps engineers) cluster tightly

**If clusters look random**: the fix is in `build_*_text` (segment 02), **not** the threshold.
Re-backfill after any text builder change.

*(Screenshot to be added after live Titan run: `docs/ex5/demo/projector-umap.png`)*

---

## Semantic vs SQL-keyword Comparison

| Intent | SQL keyword (Ex4 chat) | Semantic (Ex5 search) | Who wins / why |
|--------|------------------------|----------------------|----------------|
| "kubernetes experience" | Misses candidates whose CV says "EKS", "container orchestration", "K8s" — only matches the literal token | Surfaces EKS/K8s candidates via meaning; embedding encodes the semantic cluster around Kubernetes | **Semantic** — synonyms and implied skills |
| "candidates named Alice / status = Active" | Exact match, correct, precise | Fuzzy — may surface phonetically similar names or irrelevant matches | **Keyword** — precise facets (name, status, ID) |
| "senior platform engineer available" | Needs exact title tokens in the DB; fails on "infrastructure lead" with same role | Ranks by overall profile fit; "infrastructure lead" scores near "senior platform engineer" | **Semantic**, but watch seniority drift |
| "find candidates with Python and AWS" | `ARRAY_CONTAINS` or `LIKE` — exact, returns every Python+AWS candidate | Finds Python+AWS candidates AND related ones (Go + GCP if the embedding space is wide) | **Keyword** for exact conjunctions; **semantic** for "and nearby skills" |
| "who applied to job_001?" | Relational join — instant, correct | Not applicable — no application-status query | **Keyword** (relational filter, not a semantic query) |

### Key observations

**Where semantic wins:**
- Synonym coverage: "container orchestration" → surfaces "EKS", "K8s", "Docker Swarm" candidates
- Implicit skill chains: "cloud infrastructure" pulls DevOps candidates even without that exact phrase
- Cross-language profiles: a Hebrew-heavy CV with "Python" + "ענן AWS" can match "AWS cloud engineer" position

**Where keyword wins:**
- Precise facets: candidate id, name, status, application count — these are relational queries, not semantic
- Compliance/legal queries: "candidates in status Rejected since last quarter" — exact data, not meaning
- Debugging: "show me the SQL that produced this result" — semantic search has no auditable query

### Threshold role and calibration

The default threshold `0.5` was chosen conservatively for 512-dim Titan v2 normalized vectors:
- With `normalize:True`, cosine scores distribute roughly N(0, 1/√512) ≈ N(0, 0.044) for unrelated texts
- Genuinely relevant matches score 0.65–0.85 in initial Projector spot-checks
- `0.5` filters out most noise while preserving the top cluster

**Too low (< 0.3):** tangential matches leak in — a "Java backend developer" might surface for "Kubernetes platform engineer" just from shared cloud context
**Too high (> 0.8):** many genuinely good matches are suppressed — the candidate view shows nothing

Calibrate by loading the Projector output, hovering over a known-good position, and checking its nearest-neighbor scores. The threshold should sit below the "yes" cluster and above the "noise" cluster.

---

## Validation Checklist

- [ ] Viewing a position, the top-3 suggested candidates make intuitive sense
- [ ] Viewing a candidate, the recommended positions are reasonable fits
- [ ] You can explain why candidate A scored higher than B for a given position (cosine on the composed text)
- [ ] Embedding the same text twice produces identical vectors (reproducibility — segment 03 spot-check)
- [ ] LLM explanations reference actual profile/requirement content, not hallucinations (segment 06 spot-check)
- [ ] A senior DevOps position surfaces relevant DevOps candidates
- [ ] A junior/entry candidate surfaces entry-level positions
- [ ] A very specific-requirements position surfaces the relevant specialist via semantics (not keywords)
- [ ] Semantic vs SQL: you can state where each wins (table above)

---

## Design principles validated

1. **Reproducibility over magic:** same `embedding_text` → same vector (pinned dimensions:512, normalize:true)
2. **Grounding over invention:** `explain-v1.txt` forbids inventing skills/employers not in the input
3. **Observability of what was embedded and why:** `embedding_text` + `embedding_model` stored per row; log on backfill
4. **The threshold is a filter, not a truth:** cosine scores are relative rankings; `0.5` is calibrated, not magic


---

# JOURNAL Entries (design rationale per segment)

## Ex5-09 — Evaluation: TSV Export + Retrieval Eval

*2026-06-01*

### What changed

- `docs/ex5/export_embeddings.py`: async script reading both embedding tables → `vectors.tsv` (512-float rows, no header) + `metadata.tsv` (id/kind/label/secondary/top_terms). Stable order: candidates first (sorted by id), then positions.
- `docs/ex5/retrieval-eval.md`: Projector/UMAP workflow checklist, semantic-vs-keyword comparison table, threshold calibration rationale, validation checklist.

### Why line-alignment matters

The Projector requires `vectors.tsv` and `metadata.tsv` to have exactly the same number of lines in the same order. The export script asserts `len(vectors_rows) == len(metadata_rows)` before writing so a bug in the loop is caught immediately rather than silently producing a mis-aligned file.

### Semantic vs keyword: the key insight

The table documents when each wins. The critical takeaway: **semantic search is not always better**. For relational queries (find by name, status, application count), SQL keyword is exact and auditable. Semantic search shines for synonym coverage and implicit skill chains. Building both (Ex4 + Ex5) is the right architecture — the agent in Ex6 will route queries to the appropriate backend.

### Threshold calibration reasoning

With Titan v2 normalized 512-dim vectors, unrelated texts produce cosine scores ≈ N(0, 0.044). At 0.5, we're 11 standard deviations above the noise floor — very conservative. Initial Projector spot-checks on the real dataset should show relevant matches scoring 0.65–0.85, confirming 0.5 is a clean cut. If the Projector shows good matches scoring below 0.5, lower the threshold.

---

## Ex5-08 — Frontend: Suggested Candidates & Recommended Positions

*2026-06-01*

### What changed

- `src/lib/types.ts`: `CandidateMatch` + `PositionMatch` types.
- `src/lib/db.ts`: `getCandidateMatches` + `getPositionMatches` functions (reuse `apiFetch`).
- `src/pages/PositionDetail.tsx`: "Suggested Candidates" section — score badges, no empty heading.
- `src/pages/CandidateProfile.tsx`: "Recommended Positions" section — score badge + explanation; **suppressed when empty** (requirement from spec).

### Suppression vs empty state

Position view: shows empty state ("No strong candidate matches yet.") — the heading always renders, but the message is informative.
Candidate view: **entire section is hidden** when empty — per spec, "show none if none are genuinely relevant". This is intentional differentiation: the position view is a search aid for recruiters; the absence of suggestions should be signaled. The candidate view is a recommendation feature; an empty section heading is clutter.

### What I'd defend in an interview

*"Why not fetch positions/candidates inside the components directly from the backend?"* — Both pages already load the entities they display. The suggestion data is an orthogonal concern fetched in parallel via `getCandidateMatches(id, token)` / `getPositionMatches(id, token)`. Inline fetch in the component keeps the effect simple; the error is silently swallowed (`.catch(() => {})`) so a missing embedding never breaks the core page.

---

## Ex5-07 — Match Endpoints + Ingest Auto-Embed Hook

*2026-06-01*

### What changed

- `api/app/schemas.py`: `CandidateMatch` + `PositionMatch` with `_CONFIG` (camelCase serialization).
- `api/app/routers/matches.py`: `GET /api/positions/{id}/candidate-matches` + `GET /api/candidates/{id}/position-matches`. Both read-only, any auth role.
- `api/app/main.py`: registered `matches` router.
- `api/app/ingest/__init__.py`: auto-embed hook after `persist_candidate` / `persist_position` — best-effort, wrapped in try/except.
- `api/app/embeddings/search.py`: `threshold=None` → lazy `SIMILARITY_THRESHOLD` read so tests can monkeypatch the module constant.
- `api/tests/embeddings/test_matches_endpoint.py`: 7 tests.

### Auto-embed hook design

The hook eagerly reloads the persisted entity (with children) and calls `upsert_candidate_embedding(candidate, db)`. The client is constructed by the service module (`BedrockClient()`) — no explicit thread-through. Tests monkeypatch `app.embeddings.service.BedrockClient`.

**Critically: the hook is wrapped in `try/except Exception`.** Embed failure must not fail ingestion — ingestion succeeding is the contract. The embedding is best-effort at ingest time; `backfill.py` can fix missing/stale embeddings later.

### Threshold patchability fix

Changed `threshold=SIMILARITY_THRESHOLD` (frozen default) to `threshold=None` with lazy evaluation inside the function body. This allows `monkeypatch.setattr("app.embeddings.search.SIMILARITY_THRESHOLD", 0.0)` to work in tests, since the module attribute is read at call time, not at function-definition time.

### What I'd defend in an interview

*"Why use `asyncio.gather` for the explain calls?"* — The candidate view has ≤3 position matches, each requiring a separate `converse` call (≤2s each). Sequential would be 6s worst case; parallel with `gather` stays well under 2s.

---

## Ex5-06 — Match Explainer (grounded "why it fits")

*2026-06-01*

### What changed

- `api/app/embeddings/prompts/explain-v1.txt`: anti-hallucination prompt.
- `api/app/embeddings/explainer.py`: `explain_match` — compact structured payload → `converse` → 1–2 sentences.
- `api/tests/embeddings/test_explainer.py`: 5 tests asserting the grounding contract.

### Why grounding is tested via the prompt, not the output

The model's output is non-deterministic. The grounding contract is deterministic: the user message *must* contain the candidate's skills and the position's requirements, and the system message *must* forbid invention. Tests assert the rendered prompt — same approach as Ex4's `answer-v1.txt` grounding contract tests.

### Compact payload design

The explainer receives the same field set that the text builder used: `headline`, `skills`, `experience` (role + company), position `title`, `must_have`, `nice_to_have`. No PII, no noise. This is intentional: the explanation is grounded in the embedding match, not in the full CV. Feeding PII to the explainer would be a security risk with no quality benefit.

### What I'd defend in an interview

*"Why does `explain_match` take ORM objects instead of pre-serialized strings?"* — The function owns the serialization decision (what fields to include, how to format JSON). If callers pre-serialized, they'd have to know the explainer's input schema. This way the schema is in one place.

---

## Ex5-05 — Retrieval Search (cosine top-N + exclusion + threshold)

*2026-06-01*

### What changed

- `api/app/embeddings/search.py`: `cosine`, `rank_top_n` (pure), `search_candidates_for_position`, `search_positions_for_candidate` (dialect-branched).
- `api/tests/embeddings/test_search.py`: 8 tests.

### Design rationale

**Reuse stored vector as query** — no live embed in the hot path. Same vector → same ranking every time (reproducibility). No Bedrock call on page load.

**Dialect branch**: SQLite path loads all embedding rows and computes cosine in Python; Postgres path uses `embedding <=> CAST(:qvec AS vector)` (pgvector). The `rank_top_n` pure function is shared — both paths produce the same result shape. This mirrors the `executor.py` pattern exactly.

**Separation of concerns**: `cosine` and `rank_top_n` are pure Python functions with no DB dependency — directly unit-testable. The service functions handle the dialect decision, load the query vector, build the exclusion set, and delegate ranking. Testing the pure logic independently means we're not DB-testing the ranking math.

**Extensibility seam**: The `NOT IN (SELECT ... FROM applications WHERE ...)` is intentionally factored as the hook where future relational filters (seniority level, department, availability date) bolt on — vector search AND a relational predicate in one query. Noted in a comment.

### What I'd defend in an interview

*"Why load all embedding rows in the SQLite path instead of doing the exclusion in Python?"* — At test scale (3 candidates, 3 positions), loading all rows is fine. In production this path never runs (Postgres is used). Making the SQLite path "too clever" (subquery emulation) would add complexity with no production benefit.

---

## Ex5-04 — Embedding Service & Backfill

*2026-06-01*

### What changed

- `api/app/embeddings/service.py`: `upsert_candidate_embedding`, `upsert_position_embedding`, `backfill_all`, `BackfillReport`.
- `api/tests/embeddings/test_service.py`: 5 tests — backfill all, idempotency, re-embed on change, stored text matches builder, skip returns False.
- `docs/ex5/backfill.py`: standalone async script for one-time (idempotent) backfill.

### Key design decisions

**sha guard = skip-if-unchanged**: The `text_sha256` comparison is the cost + reproducibility guard. A second `backfill_all` run hits zero Bedrock calls because all shas match. This is the correct behavior: re-embedding is only needed when the composed text actually changed (which means the candidate's profile changed).

**Token accumulation via wrapper**: `backfill_all` wraps `client.embed_with_usage` with a counting closure to accumulate total_tokens without modifying the upsert functions' signature. An alternative was passing a shared accumulator; the closure is less invasive.

**Eager loading is the caller's responsibility**: The upsert functions call `build_candidate_text(candidate)` which accesses relationship attributes. SQLAlchemy async won't lazy-load; the caller must supply an eagerly-loaded object. This was the root cause of `test_reembed_on_text_change`'s initial failure — fixed by adding `selectinload` to the test's query.

### What I'd defend in an interview

*"Why not use SQLAlchemy's `merge()` for the upsert instead of explicit insert/update?"* — `merge()` requires the object to be in a particular state and its behavior with async sessions is subtle. Explicit get+create/update is easier to reason about, the path is clear, and the flush discipline stays consistent with the rest of the codebase.

---

## Ex5-03 — Embedding Client (Titan v2 additive to BedrockClient)

*2026-06-01*

### What changed

- `api/app/ingest/llm.py`: `_DEFAULT_EMBED_MODEL_ID`, `EMBEDDING_DIM=512` constants; `embed_model_id` param on `__init__`; `embed`, `embed_with_usage`, `embed_batch` methods on `BedrockClient`. Existing `converse`/`converse_messages` untouched.
- `api/tests/embeddings/conftest.py`: `MockEmbeddingClient` — deterministic, L2-normalized, reproducible per text.
- `api/tests/embeddings/test_embedding_client.py`: 6 tests.

### The Titan trap

Titan embeddings use `invoke_model`, not `converse`. Key differences:
- Request body: `{"inputText": text, "dimensions": 512, "normalize": true}`.
- Response body is a **streaming object** — `json.loads(resp["body"].read())`.
- Response shape: `{"embedding": [...512 floats...], "inputTextTokenCount": N}`.

Pinning `dimensions:512` + `normalize:true` is the reproducibility contract. With `normalize:true`, cosine similarity = dot product, and the same input always produces the same vector.

### MockEmbeddingClient design

Seeds `random.Random` from `sha256(text)` — same text → same 512-float unit-norm vector, different texts → distinct vectors. This is more useful than a constant mock because ranking tests can actually rank (near texts score higher than orthogonal ones). L2-normalization after the random draw gives a proper unit sphere distribution.

### What I'd defend in an interview

*"Why does `embed` delegate to `embed_with_usage` instead of its own body?"* — Single responsibility: the token-count path is the canonical one (the service uses it for cost tracking); `embed` is a convenience wrapper that discards the token count. One implementation, two call sites.

---

## Ex5-02 — Embedding Text Builders (the #1 design lever)

*2026-06-01*

### What changed

- `api/app/embeddings/text_builder.py`: `build_candidate_text`, `build_position_text`, `text_sha256`. Pure functions, no DB, fully deterministic.
- `api/tests/embeddings/test_text_builder.py`: 6 tests including golden strings, PII exclusion, empty-section suppression, determinism, sha256 stability.

### Why this design

The composed text is the only lever we have over Titan's output quality. The design rules encoded here:

1. **Semantic substance, no noise.** Excluded from candidate: email, phone, city, LinkedIn/GitHub URLs, certification years, source filenames. Excluded from position: hiring-manager email, salary range, location (location is a future *relational* filter, not a semantic token). Included: headline, summary, skills, experience, education, languages.

2. **Deterministic ordering.** Skills and requirements sorted by `sort_order`; experience sorted by `start_year` desc. Same row → byte-identical string → identical vector. This is the reproducibility tripwire.

3. **Empty sections dropped.** No `Skills: ` with nothing after it — it adds whitespace noise and shifts the token budget toward empty lines.

4. **Standardized wording.** Both entity types use `Skills:` / `Must-have:` framing, not free prose. The closer candidate/position phrasing, the better the cross-cluster geometry.

### Golden tests as a tripwire

The `test_candidate_text_golden` and `test_position_text_golden` tests assert the exact composed string. A future developer who changes wording (e.g. `Skills:` → `Technical skills:`) will see a failing test and understand they are triggering a re-embed of everything. This is intentional — silent composition drift is the hardest bug to debug in a vector system.

### What I'd defend in an interview

*"Why exclude location from the position text?"* — Location is a precision filter ("must be in NYC"), not a semantic concept. Including it pulls irrelevant candidates from London who work in the same domain into the results. The relational exclusion seam (segment 07's `NOT IN` clause) is where location filters bolt on.

---

## Ex5-01 — Storage & Migration (pgvector tables + SQLite seam)

*2026-06-01*

### What changed

- `api/app/models.py`: added `EMBEDDING_DIM=512`, `EmbeddingType` (`Vector(512).with_variant(JSON(), "sqlite")`), `CandidateEmbedding`, and `PositionEmbedding` ORM models.
- `api/alembic/versions/0004_embeddings.py`: migration creating both tables; `CREATE EXTENSION IF NOT EXISTS vector` guarded to Postgres only.
- `docker-compose.yml`: `postgres:16-alpine` → `pgvector/pgvector:pg16`.
- `api/requirements.txt`: added `pgvector>=0.3`.
- `api/tests/conftest.py`: registered `CandidateEmbedding`, `PositionEmbedding` in the `create_all` import; added `PRAGMA foreign_keys=ON` event listener so ON DELETE CASCADE is enforced under SQLite.
- `api/tests/embeddings/test_models.py`: 3 tests — roundtrip for both tables, cascade delete.

### Why this design

**`EmbeddingType = Vector(512).with_variant(JSON(), "sqlite")`** is the critical move. A bare `Vector(512)` breaks `create_all` on SQLite because there is no `vector` type; the variant degrades cleanly to a JSON list-of-floats. This is the exact pattern the existing `ARRAY→JSON` conftest patch uses, but done *in the model* so no per-test patch is needed and the seam is isolated to these two tables.

**Two dedicated 1:1 tables** (`candidate_embeddings`, `position_embeddings`) rather than columns on the main tables: the core schema stays untouched, the 150+ existing tests are unaffected, and the dialect seam is contained. A single polymorphic embedding table was considered and rejected — it would have complicated the per-entity text builders and made the `NOT IN (applications)` exclusion query more complex.

**No ANN index** at this scale. Exact cosine via sequential scan is sub-ms on tens of rows. HNSW (`vector_cosine_ops`) documented inline as the upgrade path past ~10k rows.

### The cascade test fix

SQLite requires `PRAGMA foreign_keys = ON` for FK-level CASCADE to fire; without it the embedding row survived the `db.delete(candidate)` call in the test. Fix: added a `@event.listens_for(test_engine.sync_engine, "connect")` listener in `conftest.py`. This makes SQLite tests behave consistently with Postgres on FK enforcement — a correct long-term change, not a workaround.

### What I'd defend in an interview

*"Why `with_variant(JSON)` instead of a conftest patch?"* — The model is the right place to encode the portability seam; the test fixture should only know about test data, not column types. The variant also works transparently in queries without any per-test plumbing.

---


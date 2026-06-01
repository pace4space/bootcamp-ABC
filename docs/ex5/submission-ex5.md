# Ex5 Submission — Semantic Search with Embeddings

## 1. Embedding Architecture Diagram

`docs/ex5/demo/ex5-embedding-architecture.drawio.png` (source: `ex5-embedding-architecture.drawio`)

The diagram shows all five stages:

| Stage | What | Detail |
|-------|------|--------|
| ① Text composition | `build_candidate_text()` / `build_position_text()` | Includes: headline, summary, skills (sort_order), experience (start_year desc), education, languages. Excludes: email, phone, city, URLs, salary, location. Deterministic ordering → same row → same sha256 → same vector. |
| ② Embedding model | `BedrockClient.embed_with_usage()` via `invoke_model` | Amazon Titan `titan-embed-text-v2:0`, dimensions=512, normalize=true. Returns `list[float]` + `inputTextTokenCount`. |
| ③ Vector storage | `candidate_embeddings` / `position_embeddings` tables | Columns: `embedding vector(512)`, `embedding_text text`, `text_sha256 char(64)`, `embedding_model text`, `updated_at timestamp`. FK ON DELETE CASCADE. SQLite degrades to JSON via `with_variant`. |
| ④ Similarity search | `search_candidates_for_position()` / `search_positions_for_candidate()` | **Distance metric: cosine similarity** — `score = 1 − (a⃗ · b⃗)` (inputs are L2-normalised so it reduces to dot product). Postgres: `embedding <=> :qvec` (pgvector). SQLite: `cosine()` in Python. Relational exclusion: `NOT IN (SELECT candidate_id FROM applications WHERE position_id=:pid)`. |
| ⑤ Ranking / response | `rank_top_n()` + optional `explain_match()` | **Threshold: 0.5** (env `EMBED_SIM_THRESHOLD`). Sort desc, cap top_n=3. Candidate view adds `BedrockClient.converse()` grounded explanation. |

---

## 2. TensorFlow Projector Screenshot

`docs/ex5/demo/projector-umap.png`

**Dataset:** 7 candidates + 5 positions (12 points), 512-dim mock vectors (sha256-seeded unit-norm via `MockEmbeddingClient`). The mock client is the same implementation used in all 40 automated tests — deterministic and L2-normalised, but **not semantically trained**.

**What I observe:**
- Loose domain groupings appear even with mock vectors: Alice Chen (Senior DevOps) and Eva Müller (Junior DevOps) sit near the DevOps Engineer position on the right side. Senior Platform Engineer and ML Platform Engineer cluster on the left with Bob Levy (DevOps/Infra).
- Carol Singh (Frontend) is isolated top-right near the Frontend Engineer position.
- Frank Liu (Data) and the Data Engineer position are in the centre-right group.
- Grace Teller (ML Engineer) sits close to the DevOps Engineer position bottom — the mock hash for her text happened to produce a nearby vector.

**Caveat:** with hash-seeded random vectors, clustering is partially coincidental. Real Amazon Titan v2 embeddings encode semantic proximity: "Kubernetes" and "EKS" would produce nearby vectors because the model was trained on text where these co-occur. The mock projection validates that the export pipeline (`export_embeddings.py`) works and the vector shape is correct; it does not validate retrieval quality. A live run with real Bedrock credentials would show sharper clusters — DevOps/Platform profiles pulling together tightly, with no overlap into the Data or Frontend clusters.

---

## 3. Git Log

```
* c54ebdd docs(ex5): NotebookLM source bundle — overview + retrieval-eval + journal
* a1f8c98 docs(ex5): draw.io diagrams — embedding pipeline + data model
* 2d6a5d3 feat(ex5-09): TSV export + retrieval evaluation doc
* 6058a73 feat(ex5-08): frontend: suggested candidates + recommended positions
* 66dbf0e feat(ex5-07): match endpoints + ingest auto-embed hook — 7/7 tests
* 76dd72f feat(ex5-06): grounded match explainer — 5/5 tests
* 38d09b5 feat(ex5-05): vector search + exclusion + threshold — 8/8 tests
* 85b2113 feat(ex5-04): embedding service + backfill (sha guard, idempotent) — 5/5 tests
* fa4ab26 feat(ex5-03): Titan embed on BedrockClient + MockEmbeddingClient — 6/6 tests
* b8720b7 feat(ex5-02): deterministic embedding text builders — 6/6 tests
* dd82d70 feat(ex5-01): pgvector embedding tables + SQLite seam — 3/3 tests
```

**40 new tests across 9 segments. Full suite: 188/188 passing.**

---

## 4. What Happens Behind the Scenes — "Suggested Candidates"

When a recruiter opens a position page, the frontend fires `GET /api/positions/{id}/candidate-matches`. On the backend, `search_candidates_for_position()` first loads the **stored embedding vector** for that position from the `position_embeddings` table — this vector was generated during ingest by calling `build_position_text()` (which concatenates title, seniority, description, must-have and nice-to-have requirements into a standardised string) and then passing that string to Amazon Titan's `invoke_model` API (512-dim, normalize=true). At query time no live Bedrock call is made; the stored vector becomes the query. Next, the function builds an **exclusion set** from the `applications` table — any candidate already linked to this position is filtered out before scoring. Then, for each row in `candidate_embeddings`, the backend computes **cosine similarity** between the position vector and the candidate vector: `score = dot(pos_vec, cand_vec)` (valid because both vectors are L2-normalised). Results below the **threshold of 0.5** are suppressed, the survivors are sorted descending, and the top 3 are returned as `list[CandidateMatch]` with full name, headline, and score.

A strong candidate might **not appear** for three distinct reasons: (1) **not embedded** — if the candidate was ingested before `backfill.py` ran and the auto-embed hook failed silently, their `candidate_embeddings` row is missing and they score zero; (2) **already linked** — they applied to this position and are excluded by the relational join even if they're a perfect semantic match; (3) **below threshold** — their cosine score is < 0.5, meaning their `embedding_text` and the position's `embedding_text` share too little vocabulary in the 512-dim space. The third case is the most subtle: it's not that the candidate is a bad fit — it's that the text we fed to the model didn't encode the overlap. A candidate whose CV says "EKS specialist" scores below 0.5 for a position requiring "Kubernetes skills" only if the model didn't learn that EKS implies Kubernetes, or if the `build_candidate_text()` function stripped the word Kubernetes entirely. This is why the text builder is the #1 design lever: the threshold is a filter, not a truth.

---

## Submission Checklist

- [x] Architecture diagram — 5 labelled stages, distance metric (cosine), threshold (0.5)
- [x] UMAP projection — 12 points, mock vectors, clustering observed + caveated
- [x] Git log — 11 Ex5 commits, feat(ex5-01)…feat(ex5-09) + docs
- [x] One paragraph — text composition, cosine similarity, 3 reasons a strong candidate doesn't appear
- [x] 40 new tests, 188/188 passing
- [x] draw.io pipeline + data-model diagrams (`docs/ex5/`)
- [x] `backfill.py` + `export_embeddings.py` scripts (`docs/ex5/`)
- [x] `retrieval-eval.md` — semantic vs SQL-keyword comparison + validation checklist

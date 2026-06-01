# Segment 09 — Evaluation (TSV export + Projector/UMAP + retrieval-eval)

**Depends on:** 04 (embeddings exist in the DB). Independent of 05–08 — can run as soon as backfill is done.

## Purpose

Validate embedding **quality visually before trusting retrieval**, and document where semantic search wins and
loses versus the Ex4 SQL-keyword search. Per the brief: if clustering looks random, the fix is the
`embedding_text` composition (segment 02), **not** the threshold.

## Public artifacts

### 1. TSV export (`docs/ex5/export_embeddings.py`)
A standalone async script (outputs belong in `docs/ex5/`, not `/tmp`) that reads both embedding tables via the
async engine (`from app.db import engine` / `AsyncSessionLocal`, `db.py:40,53`) and writes two
line-aligned files into `docs/ex5/`:
- **`vectors.tsv`** — one row per record, tab-separated 512 floats, **no header** (Projector format).
- **`metadata.tsv`** — header row + one row per record, same order as `vectors.tsv`:
  `id`, `kind` (`candidate`|`position`), `label` (full_name | title), `secondary` (headline | seniority),
  `top_terms` (top skills | must-haves).
- Order MUST match line-for-line between the two files. Emit all candidates first, then all positions (stable).

### 2. Evaluation write-up (`docs/ex5/retrieval-eval.md`)
- **Projector/UMAP workflow:** load `vectors.tsv` + `metadata.tsv` at https://projector.tensorflow.org
  ("Load" → vectors then metadata), switch projection to **UMAP**, color by `kind`. Record observations +
  a screenshot (`docs/ex5/demo/projector-umap.png`).
- **Clustering checklist** (what "good" looks like):
  - DevOps/platform candidates cluster together; frontend candidates form a separate cluster.
  - Each position sits near the candidates that should match it (a position's nearest neighbors are sensible).
  - Archived/off-topic records sit apart rather than scattered through good clusters.
  - If clusters look random → revise `build_*_text` (segment 02), re-backfill, re-export. **Not** the threshold.
- **Semantic vs SQL-keyword comparison:** run the same intents through Ex4 chat and Ex5 search and tabulate:
  | Intent | SQL keyword (Ex4) | Semantic (Ex5) | Who wins / why |
  |--------|-------------------|----------------|----------------|
  | "kubernetes experience" | misses "EKS"/"ECS"-only CVs | surfaces them via meaning | semantic (synonyms/implied skills) |
  | "candidates named X / status = Active" | exact, correct | fuzzy, may over-match | keyword (precise facets) |
  | "senior platform engineer" | needs exact title tokens | ranks by overall fit | semantic, but watch seniority drift |
  - Articulate the threshold's role: too low → tangential matches leak in; too high → the candidate view
    suppresses real matches. Justify the chosen `0.5` (or the calibrated value) with what you saw in Projector.

### 3. Validation checklist (fill in during the live demo — the brief's self-check)
- [ ] Viewing a position, the top-3 suggested candidates make intuitive sense.
- [ ] Viewing a candidate, the recommended positions are reasonable fits.
- [ ] You can explain why candidate A scored higher than B for a given position (cosine on the composed text).
- [ ] Embedding the same text twice produces identical vectors (reproducibility — segment 03 spot-check).
- [ ] LLM explanations reference actual profile/requirement content, not hallucinations (segment 06 spot-check).
- [ ] A senior DevOps position surfaces relevant DevOps candidates.
- [ ] A junior/entry candidate surfaces entry-level positions.
- [ ] A very specific-requirements position surfaces the relevant specialist via semantics (not keywords).
- [ ] Semantic vs SQL: you can state where each wins (the table above).

## Reused utilities
- Async engine / session — `api/app/db.py:40,53`.
- `_EAGER` eager-load for `top_terms` — `api/app/routers/candidates.py:32`.
- Submission-doc precedent (diagram + git log + demo Q&A) — `docs/ex4/submission-ex4.md`.

## Demo / verify
- `python docs/ex5/export_embeddings.py` → `docs/ex5/vectors.tsv` + `docs/ex5/metadata.tsv`, equal line counts.
- Load into Projector, switch to UMAP, confirm the clustering checklist; save the screenshot.
- Complete `docs/ex5/retrieval-eval.md` with the comparison table + the validation checklist results.

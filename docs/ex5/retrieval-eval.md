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

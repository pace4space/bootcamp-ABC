# Segment 02 — Embedding-Text Builders (the #1 design lever)

**Depends on:** 01 (imports the new models for type hints; can also accept lightweight inputs). **Blocks:** 04, 06.

## Purpose

Compose the **standardized, deterministic, low-fluff** string that gets embedded for each candidate and
each position. Titan is a black box — *this text is the only thing we control*, and it determines retrieval
quality far more than any threshold. Two pure functions, no DB, no I/O, fully unit-testable. Determinism here
is what makes "same input → same vector" true (Principle 1).

## Public artifacts (`api/app/embeddings/text_builder.py`)

```python
def build_candidate_text(candidate) -> str: ...
def build_position_text(position) -> str: ...
def text_sha256(text: str) -> str: ...   # hex digest; the drift / skip-if-unchanged signal
```

Inputs are ORM objects (`Candidate`, `Position`) with eager-loaded children (skills, experience,
requirements). Keep the functions tolerant of `None`/empty children so they work on partial profiles.

### `build_candidate_text` — fixed section order

```
Role: {headline}
Summary: {summary}
Skills: {skill names, joined ", ", ordered by sort_order}
Experience:
- {role} at {company} ({start_year}–{end_year or 'present'}): {"; ".join(highlights)}
- ...                     (experience ordered by start_year desc, mirroring routers/candidates.py:56)
Education: {degree, institution}; ...        (short; no years)
Languages: {language names, joined ", "}     (optional but cheap signal)
```

### `build_position_text` — fixed section order

```
Title: {title}
Seniority: {seniority}
Description: {description}
Must-have: {must_have requirement texts, joined ", "}
Nice-to-have: {nice_to_have requirement texts, joined ", "}
```

## Composition rules (these are the design decisions — encode them, test them)

- **Include the semantic substance, exclude the noise.** Candidate: drop email, phone, city, LinkedIn/GitHub
  URLs, certification years, source filenames — they add no meaning and dilute the signal. Position: drop
  hiring-manager email, salary range, source filename, and **location** (location is a future *relational*
  filter, not a semantic token — see the extensibility seam in segment 07).
- **Deterministic ordering.** Skills/requirements in `sort_order`; experience by `start_year` desc. Same row →
  byte-identical string → identical vector. This is the reproducibility tripwire.
- **Drop empty sections entirely.** No dangling `Skills: ` with nothing after it; no `Experience:` header with
  zero bullets. Normalize whitespace (collapse runs, strip trailing).
- **Standardize wording across both entity types.** The closer the candidate/position phrasings, the better the
  cross-cluster geometry (a candidate sits *near* its matching position). This is why both use the same
  `Skills:`/`Must-have:` framing rather than free prose.

## Reused utilities
- Experience-sort precedent (`start_year` desc) — `api/app/routers/candidates.py:56-71`.
- `highlights` is `ARRAY(Text)` on the candidate experience (`models.py:163`) → already a `list[str]`.
- `hashlib.sha256(text.encode("utf-8")).hexdigest()` for `text_sha256` — stdlib, no dep.

## Tests (`api/tests/embeddings/test_text_builder.py`) — test-first
1. `test_candidate_text_golden` — for a seeded candidate (e.g. the seeded DevOps profile), assert the exact
   composed string (golden). This is the tripwire: any wording change here re-embeds everything, so it must be
   a conscious, reviewed change.
2. `test_position_text_golden` — exact string for a seeded position.
3. `test_excludes_pii` — composed candidate text contains no email/phone/URL substrings.
4. `test_empty_sections_dropped` — a candidate with no certifications/languages yields no empty headers.
5. `test_deterministic` — calling the builder twice on the same object yields identical strings.
6. `test_sha256_stable_and_sensitive` — `text_sha256(s)` stable across calls; changes when one character changes.

## Demo / verify
- `cd api && .venv/bin/pytest -q tests/embeddings/test_text_builder.py` green.
- Eyeball one composed string (a tiny script or a `-s` print) — it should read like a clean structured profile,
  not a CV dump; confirm it would embed sensibly.

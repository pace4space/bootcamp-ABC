# Data-Access Layer — Test Plan

Tests live in `src/lib/db.test.ts`. They run against `src/lib/db.ts` (the async
seam) using the fixture JSON in `src/data/`. Tests must be **RED before commit 3**
(implementation), **GREEN after**. Commit 4 replaces the fixture JSON with the real
extracted dataset without touching this test file.

## Required cases (from the plan)

### (a) `getCandidates` returns only Active candidates
- Feed: one Active candidate (`cv_001`), one Archived (`cv_002`).
- Assert: result has length 1 and `result[0].id === "cv_001"`.
- **Why it matters:** The Candidate List screen filters to Active; Archived records
  must be invisible to the user without a backend-enforced permission boundary.

### (b) `getApplicationsByCandidate` resolves M:N correctly
- Feed: two applications both belonging to `cv_001`; `cv_002` has none.
- Assert (M:N): `getApplicationsByCandidate("cv_001")` returns exactly 2 applications,
  and each `application.candidateId === "cv_001"`.
- Assert (empty): `getApplicationsByCandidate("cv_002")` returns `[]`.
- **Why it matters:** Both the Candidate Profile and Positions screens read this join
  from opposite directions. Wrong filtering silently corrupts both screens.

### (c) `experience` is sorted descending by `startYear`
- Feed: `cv_001` with two experience items stored *in the wrong order* in JSON
  (older entry first: 2021, 2023).
- Assert: `getCandidate("cv_001")` returns experience where `[0].startYear === 2023`
  and `[1].startYear === 2021`.
- **Why it matters:** The brief explicitly requires stable sorting so the Compare
  screen's diff is deterministic. If components sort ad-hoc, the sort is applied
  inconsistently and the diff breaks.

### (d) Candidate with no applications returns `[]` gracefully
- Feed: same as (b).
- Assert: `getApplicationsByCandidate("cv_002")` resolves to exactly `[]` (not null,
  not undefined, not an error).
- **Why it matters:** The Candidate Profile renders a "No positions" empty state; it
  must not crash on null/undefined returned from the data layer.

## Additional cases to add when the real dataset lands (commit 4)

- `getPositions` returns only Open positions (mirrors case a).
- `getApplicationsByPosition` returns only applications for the given positionId.
- `getCandidate` with an unknown id returns `null`.
- `getPosition` with an unknown id returns `null`.
- Skills are sorted alphabetically within a returned candidate.

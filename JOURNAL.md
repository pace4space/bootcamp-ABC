# Hellio HR — Exercise 1 Journal

---

## Commit 4 — Extract Demo Dataset

**What changed.** Replaced the 2-record test fixtures in `src/data/*.json` with the real demo dataset: 12 candidates, 20 positions, 11 applications. Updated `src/lib/db.test.ts` to assert against real data. Added `scripts/verify-data.mjs` (referential integrity + file existence checks). All 4 tests pass, `tsc -b` clean, `verify-data` passes with 47 OK checks.

**The 12 candidates and why I picked them.**
- cv_001–cv_008 (Aarav Hayes → Adalyn Fox): all 8 names linked in `jobs.xlsx`. These give the real M:N join data (Abel McKinney → jobs 1/3/4; Abby Macias → jobs 1/9). I needed them all for FK integrity.
- cv_100 (Athena Lynch): Archived. Gives the demo an archived candidate and a non-trivial getCandidates() filter to observe.
- cv_150 (Blaire Conley) and cv_202 (Camilla Woods): near-duplicate Senior Platform Engineers sharing almost identical summaries, highlights, and education but differing company numbers, certs, and skill sets. Chosen specifically for the Compare diff demo — they are the pair that makes the diff screen interesting.
- cv_265 (Dallas Peterson): bilingual career-changer (Hebrew RTL bullets, English headers). Chosen for the "solve-twice" exercise (by-hand vs agent-driven extraction).

**Why cv_004's experience is stored oldest-first in the JSON.**
The sort test needs a candidate with experience stored out of order in the raw JSON so the db layer's sort is actually observable. cv_004 has two entries: Systems Administrator (2019-2021) stored first, Cloud Infrastructure Engineer (2021-present) stored second. After `sort((a, b) => b.startYear - a.startYear)`, the order becomes [2021, 2019]. Without this intentional inversion, the test could pass even if the sort were removed.

**Why I updated the test expectations (not just the data).**
The original tests were written for a 2-record fixture: 1 Active, 1 Archived, cv_001 with 2 apps. With 12 real candidates the old `toHaveLength(1)` and `result[0].id === 'cv_001'` assertions would break on count, not on filtering logic. The real invariants are: (a) every returned candidate has status Active and cv_100 is absent; (b) cv_004 has exactly 3 apps; (c) experience is sorted desc by startYear; (d) cv_100 returns []. These test the same four contracts from commit 2's test plan — just anchored to real data instead of a minimal fixture.

**The xlsx discrepancy I documented and resolved.**
`jobs.xlsx` row 1 has `sarah.chen@tech-innovate.io` but the email file says `sarah.chen@company.com`. The extract-position.md worked example uses the email file value (`@company.com`), which I followed for consistency. The xlsx Hiring Manager column appears to have a different domain for job_001 — this is a synthetic dataset inconsistency. Recorded here; no action needed until Ex3's automated pipeline needs to decide authoritatively.

**Honest gaps in this extraction.**
- Hebrew RTL bullets in cv_265 were extracted via `pdftotext` which scrambles RTL ordering. The highlights are present verbatim but their order in the JSON may differ from what a multimodal model would extract from the original PDF. This is intentional — the solve-twice exercise (cv_265 by hand vs agent-driven) will quantify exactly this gap.
- cv_265's Hebrew summary says "Computer Science graduate" but the Education section says "B.A. in Business Administration." I used the Education section value (specific, structured) and noted the contradiction here. The agent extraction in the solve-twice exercise may or may not catch this.
- cv_007 (Ada Montes) has "B.Sc. in Computer Science (In Progress)". `EducationItem.endYear` is `number`, not nullable — so I used 2026 as the projected completion year. A better fix in Ex2 would be to make `endYear: number | null` on EducationItem as well.
- Two positions (job_010, job_017) are marked Closed to demonstrate the Open filter in getPositions(). This is arbitrary — the source data has no closed indicators — but it gives the Positions list something to filter and is noted as manually assigned ("will be derived by the backend in Ex2").

**The `uv run --with` pattern used here.**
Python was needed for two one-off tasks (reading jobs.xlsx, extracting cv_202.docx). Rather than `pip install` into the system, I used `uv run --with openpyxl` and `uv run --with python-docx` — ephemeral envs, dependency declared at the callsite, no persistent install, reproducible for anyone cloning the repo. This is the `uv` equivalent of the project's "no new dep without asking" rule: use what you need, don't pollute the environment.

For my own review — to defend every decision in an interview later.
One entry per commit.

---

## Commit 3 — Data Layer (GREEN)

**What changed.** Replaced the stub bodies in `src/lib/db.ts` with correct
implementations. All 4 tests pass, `tsc -b` clean. Zero test or type file changes —
the contract didn't shift between RED and GREEN.

**The four implementations.**
- `getCandidates` → `.filter(c => c.status === 'Active')`. One line; the simplicity
  is the point. When Ex2 replaces this with `fetch('/candidates?status=Active')`, the
  caller sees no difference.
- `getCandidate(id)` → find by id, then return a shallow copy with experience sorted
  `b.startYear - a.startYear` (spread + sort so the source array is never mutated).
  Sorting here — in the data layer — keeps components free of sort logic. I originally
  sorted by `endYear` (thinking "most recently ended" is more intuitive), but the plan
  says `startYear desc` and it's simpler to defend. Changed back.
- `getApplicationsByCandidate(candidateId)` → `.filter(a => a.candidateId === candidateId)`.
  Exactly what test (b) and (d) were measuring.
- `getApplicationsByPosition`, `getPositions`, `getPosition` → symmetric filters.

**Why sort in the data layer, not in the component.** If a component sorts, every
component using this data must remember to sort. If two components use slightly
different sort keys, the Compare diff breaks (same candidate, different experience
order, diff sees every item as different). Sorting once in `getCandidate` is the only
place it can be guaranteed consistent. This is the brief's "normalize ... with stable
sorting" hint in action.

**The async seam is correct.** Both stub and implementation are `async`. The tests
`await` every call. This means test (d)'s `toEqual([])` tests the *resolved value*,
not a promise — which is exactly what the UI will do. Zero change to test wording
needed when Ex2 swaps to `fetch()`.

---

## Commit 2 — Data Layer Tests (RED)

**What changed.** Added `docs/db-test-plan.md` (the four required cases in English, written before any test code), `src/data/*.json` (minimal fixtures: 2 candidates, 2 positions, 3 applications), `src/lib/db.ts` (stub — correct signatures, no filtering or sorting), and `src/lib/db.test.ts` (4 failing assertions). All 4 tests are RED before implementation.

**Why write the test plan first, before the test file.** The test plan in English forces me to state exactly what the contract must enforce — in terms of screen requirements and failure consequences — before I've written a single assertion. If I write the test code first, I tend to test what's easy to test, not what matters. Writing the plan first identifies (d) "empty array" as a distinct case worth testing, not just an edge case I'd skip.

**Why the test failures are meaningful (assertion errors, not import errors).** The stub exports all the correct function signatures returning raw unfiltered data. This means tests fail because the *behavior* is wrong, not because a module doesn't exist. The assertion errors (`expected 1 but got 2`, `expected [2023, 2021] but got [2021, 2023]`) directly describe what commit 3 needs to implement. A "module not found" error tells you nothing.

**The fixture design decision.** I added `app-3` for a nonexistent `cv_003` so that the unfiltered stub doesn't accidentally pass test (b). If the fixture had only 2 applications both belonging to `cv_001`, the stub returning-all would return 2 — coincidentally the right count, a false green. The extra record makes the lack of filtering impossible to hide.

**What the contract these tests encode is.** They state: the data layer, not the component, is responsible for (1) filtering by entity status, (2) filtering join data by foreign key, (3) sorting sub-lists deterministically, and (4) never returning null for an empty list. These four rules are what keep components simple and the Compare diff deterministic.

---

## Commit 1 — Data Model Types

**What changed.** Added `src/lib/types.ts` — the pure data model. No implementation,
no UI imports, no framework dependencies. Just TypeScript types. `tsc -b` clean.

**Why a separate types file with no implementation.** The brief: *"treat the candidate
profile as a pure data model, independent of UI."* Having a single file that only
declares shapes means: (a) any file that imports it gets the contract without pulling
in business logic; (b) when Ex2 introduces a Postgres-backed FastAPI, the same types
file describes both the JSON fixture and the API response shape — no duplicate modeling.

**The three-entity structure and why it maps to three future DB tables.** Candidate,
Position, Application — each maps to a future Postgres table. This isn't over-design;
the exercise explicitly says "hardcode JSON now, add the backend in Ex2." Modeling the
JSON as if it were already relational means the mental model transfers intact.

**Why Application is a join entity (the question I most expect).** Three reasons I can
defend independently:
1. *It's M:N in the actual data.* Abel McKinney appears in jobs 1, 3, and 4. A
   `positionIds[]` array on Candidate or a `candidateIds[]` on Position would force
   you to update two places for one logical relationship — guaranteed drift.
2. *The relationship carries its own attribute.* `status` (Waiting/Rejected) is a
   property of "Abel McKinney FOR this specific position." He can be Rejected for job 9
   and Waiting for job 1 simultaneously. Status does not belong on either parent entity;
   it belongs on the pair. This is the textbook case for a join entity.
3. *Both screens read it from opposite directions.* The Positions screen needs
   `position → its candidates + their statuses`. The Candidate screen needs
   `candidate → its positions + their statuses`. A single Application entity serves
   both without denormalizing into arrays on each side.

**Per-field justification (the fields I'd have to explain).**
- `Candidate.status: "Active"|"Archived"` — the brief's "list all Active candidates"
  filter. Assigned manually in JSON Ex1; backend derives it in Ex2. I chose two values
  (not a boolean) because "archived" is a named concept worth tracking, not just false.
- `ExperienceItem.endYear: number | null` — `null` = Present. Kept numeric (not the
  string "Present") so the db layer sorts purely numerically without string comparison.
- `Language.proficiency: string` — free string, not a union. The data shows "Native",
  "Professional", "Fluent", "Advanced" and possibly others. Locking it to a union forces
  me to invent/normalize values during extraction — wrong direction.
- `Application.status: ApplicationStatus | null` — `null` models the blank-status rows
  in jobs.xlsx (candidates listed with no HR action yet). Safer than adding a `"Pending"`
  string I'd have to map back and forth.
- `CandidateDiff` in types.ts — stub added here so the Compare screen (commit 8) imports
  from the types contract, not from a utility file. Small, but keeps the boundary clear.

**What I'd change with hindsight.** `contact` is an inline object type, not a named
type alias. If future fields are added (e.g. Slack handle), finding all usages is
harder. A named `ContactInfo` type would be cleaner. Left as-is for now to avoid
over-engineering; refactor candidate in Ex2.

---

## Commit 0 — Scaffold

**What changed.** `git init`; planning docs split into `docs/plan-v1.md` and
`docs/plan-v2.md`; scaffolded Vite + React 19 + TypeScript; added React Router v7,
Tailwind v4 (`@tailwindcss/vite`), and Vitest; removed the Vite demo cruft; created
the source layout (`src/{pages,components,context,lib,data}`); copied the original
CVs and job emails into `public/cvs` and `public/jobs` (immutable); scaffolded an
empty `ApplicationsContext` provider; built the app shell (header + nav) with five
routed page placeholders. `tsc -b` and `npm run build` both pass.

**Why Vite SPA over Next.js.** The backend belongs to Exercise 2 (FastAPI). So Ex1
should be pure UI plus one swappable data module (`src/lib/db.ts`). In Ex2 I change
only that module's internals from JSON-import to `fetch()`; the UI never changes.
Next.js would have me write route-handler/server code that FastAPI then makes
throwaway, plus the server/client-component split — more concepts to defend, some
discarded. The clean swap-seam wins.

**Why the `lib/db.ts` seam.** A single async boundary between UI and data. Async now
(even though the source is a local JSON import) so the function signatures already
match the network-backed Ex2 version — zero UI churn at the swap.

**Why the provider exists from day 1.** Add/remove-position needs shared, mutable,
in-memory state. I scaffold `ApplicationsContext` empty in commit 0 so the provider
boundary is in place; commit 9 fills it with the working copy + mutators. Introducing
a new provider at the top of the tree late would touch `main.tsx` and risk churn.

**Why Tailwind over CSS Modules.** Utility classes co-locate style with markup (one
component audited in one place), eliminate the JSX↔CSS class-name drift failure mode,
and are reliably generated. Tradeoff accepted: the utility vocabulary is itself a line
I must own — it's not magic-free, just denser and co-located.

**Honest note.** The original CVs/jobs are copied into `public/` so the running app can
link to them; the source `CVsJobs/` folder stays untouched as the system of record.

# Hellio HR — Exercise 1 Journal

---

## Commit 8 — Compare Screen (Side-by-Side Candidate Diff)

**What changed.** Implemented `/compare?a=cv_150&b=cv_202` — a side-by-side diff of two candidates loaded from query params. Sections: paired header cards, skill diff (shared / only-A / only-B), experience columns, education columns, certifications columns. Demo pair: cv_150 (Blaire Conley) vs cv_202 (Camilla Woods) — near-duplicate Senior Platform Engineers with identical role history but different tool breadths.

**Why Set operations on `skill.name`, not `skill.id`.** Ids are stable within a single candidate record (`skill-1`, `skill-2`, …) but they're not globally unique across candidates — two different candidates can each have a `skill-1` for completely different skills. The meaningful identity for comparison is the skill's name (e.g. `"Terraform"`). Using `new Set(b.skills.map(s => s.name))` as the membership test and filtering `a.skills` by that set produces `sharedSkills`, `onlyInA`, and `onlyInB` with correct semantics. The `CandidateDiff` type (already declared in `lib/types.ts` from commit 1) carries these three fields.

**Experience sort stability comes for free.** The db layer sorts experience by `startYear` descending for every `getCandidate()` call. Because both candidates were loaded through the same function, their experience arrays are already in the same order. The diff renders a straight column for each — no sorting logic needed in the component. This is the concrete payoff of "sort once in the data layer, not in components."

**Query params over a new route.** `/compare/:a/:b` would work but buries the candidate ids in the URL path, making it awkward to link to directly. `/compare?a=cv_150&b=cv_202` is bookmarkable, copy-pasteable, and navigable without needing a form. `useSearchParams()` from React Router v7 reads them cleanly.

**Graceful edge cases.** Three states beyond the happy path: (1) no params → instructional prompt with example URL and back link; (2) one param missing (only `a` or only `b`) → same prompt (same guard: `!aId || !bId`); (3) valid params but id not found → not-found message with the unknown id shown. All three render without crashing.

**What I'd defend in an interview.** "Why not diff experience items?" — experience entries don't have stable cross-candidate identifiers, so structural diff (which item matches which?) requires either string-matching on role/company or an alignment algorithm. For this exercise the side-by-side visual is sufficient; the near-dup pair (same roles, same years, different company names) makes the pattern obvious without algorithmic alignment. Adding it would be premature. For Ex4 (deterministic search/reporting), role-level matching is worth revisiting.

---

## Commit 7 — Positions List + Detail Screens

**What changed.** Implemented `/positions` (Open positions list with title search) and `/positions/:id` (full position detail: header, source email link, requirements split into mustHave/niceToHave, description, linked candidates with application statuses). Extracted `AppStatusBadge` to `src/components/` — it was about to exist in two page files.

**Why extract `AppStatusBadge` now, not earlier.** In commit 6, it only existed in one file — extracting it then would have been premature (optimising for a future that hadn't arrived). In commit 7, PositionDetail needed the same component: now there are two callers and the duplication is real. "Three similar lines is better than a premature abstraction" — the right moment to extract is when the second concrete use appears.

**The `Promise.all()` pattern for linked candidates.** PositionDetail needs: the position, its applications, and the candidate record for each application. The sequential version — `await getPosition`, `await getApplicationsByPosition`, then `for (app of apps) { await getCandidate(app.candidateId) }` — makes N+2 round trips in series. Using `Promise.all(apps.map(app => getCandidate(app.candidateId)))` runs all N candidate fetches in parallel. Today this hits in-memory JSON so the difference is negligible; in Ex2 (network) the difference is N×latency vs ~1×latency. Writing it correctly now costs nothing.

**Why description uses `whitespace-pre-line`.** Position descriptions are extracted from email prose and may contain paragraph breaks (`\n\n`). `whitespace-pre-line` preserves those line breaks in HTML without requiring the source data to be HTML-escaped. Alternative: split on `\n` and render `<p>` per paragraph. `whitespace-pre-line` is one CSS property; the `<p>` approach is more markup for the same visual result. Chose the simpler path.

**The join direction.** CandidateProfile reads applications from the candidate side (`getApplicationsByCandidate`) — it needs to know "which positions has this person applied to?" PositionDetail reads from the position side (`getApplicationsByPosition`) — "which candidates have applied here?" Both directions go through the same Application join entity, no denormalization. This is the concrete payoff of the M:N join entity decision from commit 1.

---

## Commit 6 — Candidate Profile Screen

**What changed.** Implemented `/candidates/:id` — full profile render of all Candidate schema fields (header, contact, summary, skills, experience, education, certifications, languages, applications). Original CV link opens PDF in-browser or triggers download for DOCX. Not-found state renders gracefully. `AppStatusBadge` component maps all five `ApplicationStatus` values to colour-coded chips. `posMap` built from `getPositions()` so each application row shows position title, not raw id. All optional fields are guard-checked — missing fields don't render; no crashes. Architecture diagram added in `docs/architecture.md` (three Mermaid diagrams: component/data flow, ER diagram, Ex1→Ex2 async swap seam).

**Why every optional field is guard-checked, not defaulted.** The schema discipline: "optional fields are nullable and the UI must render gracefully when they're missing." Defaulting (e.g. showing "Unknown city" when `city` is absent) is wrong — it lies to the user. Hiding the field is honest. This also means any future candidate added to `candidates.json` with missing optional fields will just render a cleaner profile, not a broken one.

**Why `posMap` is built from `getPositions()` here.** Applications store `positionId` (FK), not the title. We need the title for the UI. Two options: (1) call `getPosition(id)` for each app — N sequential async calls; (2) load all positions once, build a Map, do O(1) lookup. With 20 positions and ≤11 applications, option 2 is faster and cleaner. Same pattern as `positionAppMap` in CandidatesList (commit 5): build the index once, look up cheaply per row.

**The `AppStatusBadge` component.** Extracted as a separate component — not a helper function — because it has its own type signature and colour mapping. `colors` is a plain object keyed by status string (not a switch, not a ternary chain): adding a new status means one new line, not restructuring control flow. The fallback `bg-slate-100` handles any unexpected status values without crashing.

**Honest gap.** Hebrew RTL bullets in `cv_265` render left-to-right in the `<li>` elements. The data is present and correct; the visual direction is wrong. Fix: `dir="rtl"` on the bullet string or the `<ul>`. Deferred — flagged as a known polish item (Risk #6 in plan).

---

## Commit 5 — Candidates List Screen

**What changed.** Implemented the `/candidates` route with search, position filter, and card list. Component loads Active candidates via `getCandidates()` (filter handled by db layer); renders a text search input (case-insensitive fullName match) and a position dropdown. Filter logic: `bySearch` candidates, then optionally filter to those with applications to the selected position. Position-to-candidates map built from `getApplicationsByPosition()` for each position on load. Card layout shows name, headline, skills snippet (up to 5, with "+N more" badge), and candidate id. Links to profile route `/candidates/:id` (commit 6). Empty state renders gracefully when search/filter yields no results.

**Why the positionAppMap strategy.** Filtering "candidates with applications to position X" requires a reverse lookup: given a position, find all candidates who have applied. The straightforward approach — `bySearch.filter(c => getApplicationsByPosition(selectedPositionId).map(a => a.candidateId).includes(c.id))` — makes N queries (one per candidate) or builds a new set on every filter change. Instead, `positionAppMap` is a `Map<positionId, Set<candidateId>>` built once when positions load. Lookup is O(1); the component filters in one pass. Trade-off: memory for positions × candidates (small for 12+20) vs. speed (filter is instant). No extra db queries.

**Why transforms stay in component.** Search and position filter are UI state (typing in a box, selecting a dropdown). The db layer handles "Active" filtering (data contract) and sorting (deterministic Compare diff). The component handles "user's current search term" and "user's current position selection" — ephemeral, never persisted, not part of the canonical data contract. Keeping them separate: db layer = stable, components = fast to change.

**What wouldn't scale here.** If we had 1000 candidates and 100 positions, the positionAppMap (100 Sets of IDs) + re-rendering 1000 cards on every filter change would hurt. At that point: (1) paginate the list; (2) cache the filtered result; (3) push position filtering to the db layer (SELECT candidates WHERE id IN (...) at the SQL boundary in Ex2). For 12+20, the current approach is honest.

**Dev environment fix.** Node 18 (default in the environment) doesn't support Vite 8. Upgraded to Node 22 via nvm, reinstalled node_modules, full clean build + tests pass. The PROGRESS.md summary was also added in this commit to track all completed work (commits 0–4) and pending tasks (commits 5–10).

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

# Hellio HR — Exercise 1 Journal

For my own review — to defend every decision in an interview later.
One entry per commit.

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

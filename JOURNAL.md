# Hellio HR — Exercise 1 Journal

For my own review — to defend every decision in an interview later.
One entry per commit.

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

# Hellio HR — Exercise 1

Candidate Profile Viewer & Diff. A UI-only, JSON-backed app for reviewing technical
candidate profiles, comparing two candidates side by side, and browsing open
positions. No database, no auth, no LLM in the running app — those arrive in later
exercises. See `docs/plan-v2.md` for the full design.

## Run

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # typecheck + production build
npm test         # data-layer tests (Vitest)
```

## Layout

- `src/lib/types.ts` — pure data model (Candidate, Position, Application).
- `src/lib/db.ts` — the only data-access seam; async over local JSON now, swapped to
  the FastAPI backend in Exercise 2 without touching the UI.
- `src/data/*.json` — normalized candidate/position/application data.
- `src/pages`, `src/components`, `src/context` — UI.
- `public/cvs`, `public/jobs` — original source documents (immutable).
- `prompts/` — throwaway Ex1 extraction prompts (replaced by a real pipeline in Ex3).

A full demo walkthrough is added in commit 10.

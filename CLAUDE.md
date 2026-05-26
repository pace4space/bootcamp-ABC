# Hellio HR — Exercise 1 (Candidate Profile Viewer & Diff)

First of 8 exercises building an agent-assisted HR system. Ex1 is **UI-only,
JSON-backed**: no database, no auth, **no LLM/agent in the running app**. The
full plan lives in `docs/plan-v2.md` (v1 preserved in `docs/plan-v1.md`).

The 8-exercise arc (every Ex1 decision is lived with through Ex8):
1. Candidate viewer & diff (here) · 2. FastAPI + Postgres backend · 3. LLM
extraction pipeline · 4. Deterministic search/reporting · 5. Embeddings/vector
search · 6. HR agent (Strands, Gmail MCP, human-in-loop) · 7. Templates MCP
server · 8. Managed agent deployment.

## Principles (non-negotiable)
- **Own every line.** If I can't defend a line in an interview, it shouldn't ship.
  Flag non-obvious patterns and explain them before writing.
- **Technician vs Expert:** solve the category, not just the instance.
- **Solve worthwhile things more than one way** to learn the tradeoff.
- **Token-aware model routing:** Haiku = repetitive extraction/scaffold/format;
  Sonnet = module implementation + test design; Opus = planning + doubt only.

## Architecture rules
- **Data model is pure and UI-independent.** Types in `src/lib/types.ts`; data in
  `src/data/*.json`. **Never mix UI concerns with data transformation.**
- **All reads go through `src/lib/db.ts`** — async functions over local JSON today;
  in Ex2 only their bodies change to `fetch()` the FastAPI backend. UI never knows
  the source. Do not import JSON directly into components.
- **`public/cvs/` and `public/jobs/` originals are immutable** — copied, never edited.
- Three JSON files mirror three future DB tables: candidates, positions, applications.
  `Application` is a real join entity (M:N + per-link status), not a field.

## Schema discipline
- Don't hard-code assumptions about profile shape. Optional fields are nullable and
  the UI must render gracefully when they're missing.
- Stable ids everywhere (`cv_001`, `job_001`, `skill-1`); sort lists deterministically
  (experience by `startYear` desc) so comparison is trivial.

## Stack conventions
- Vite + React 19 + TypeScript, React Router v7, **Tailwind v4 for styling — no
  separate CSS files**, React built-in state (no Redux). Vitest for the data layer.
- Functional components + hooks. **No new dependency without asking first.**

## Testing
- `src/lib/db.ts` is **test-first**: test doc → failing tests → implementation.
- UI components are not unit-tested in Ex1 (overkill at this stage).

## Workflow
- **Prompts are versioned artifacts in `/prompts/`**, not chat messages. Ex1
  extraction prompts are throwaway (replaced by the real pipeline in Ex3).
- **Commit every working step**; each commit leaves the app demo-able.
- **JOURNAL.md gets one entry per commit** — what changed, why, alternatives, and
  what I'd defend in an interview.

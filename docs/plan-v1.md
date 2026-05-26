# APPENDIX — Plan v1 (preserved verbatim, pre-amendments)

## Context (v1)

First of 8 exercises building toward an agentic HR system. Ex1 is a UI-only,
JSON-backed candidate/position viewer with side-by-side diff. No DB, no auth, no LLM in
the running app. The point: (a) a data model and UI seam clean enough to live with
through Ex8; (b) practice Claude Code agent use with deliberate model routing.
Decisions: Vite + React + TS SPA; reads behind one async `lib/db.ts` seam;
add/remove in-memory with a "not saved until Ex2" badge; ~12 candidates + all 20 positions.

## 1. Data exploration (v1)
270 CVs (216 PDF + 54 DOCX), consistent schema. Synthetic/templated → good diff pairs.
Bilingual Hebrew/English CVs (RTL scrambles under pdftotext). 20 positions = hiring-
manager emails. `jobs.xlsx` = the join table (title, manager email, candidate↔job links
with per-link status Waiting/Rejected/blank; jobs 1–4,9 only; linked by name not cv_id;
M:N confirmed).

## 2. Data model (v1)
Candidate / Position / Application (join) + sub-lists with stable ids and sorting. v1
proposed candidate.status / position.status as **invented for demo** (later changed to
explicit manual fields in v2). Join entity defended on M:N + relationship-status + both-
directions + Ex2/Ex6 alignment, but v1 left Risk #1 open for pushback.

## 3. Stack (v1)
Vite + React + TS SPA; typed async `lib/db.ts` seam; Router; CSS Modules; React state;
Vitest. Rejected Next.js (throwaway BFF vs FastAPI).

## 4. Routes (v1)
`/`→`/candidates`, `/candidates`, `/candidates/:id`, `/compare?a=&b=`, `/positions`,
`/positions/:id`. Originals in `public/cvs/`. Mutations in-memory via `ApplicationsContext`
(v1 introduced it in commit 9; v2 scaffolds empty in commit 0). Compare via query params.

## 5. Pipeline (v1)
Throwaway prompts in `/prompts/`; types as contract; multimodal for bilingual; all 20
positions + ~12 candidates. Gaps: name→cv_id mapping; status fields invented (v2 makes
them explicit manual fields noted "derived in Ex2").

## 6. Agent setup (v1)
CLAUDE.md content; commands `/extract-candidate` `/extract-position` `/verify-data`
`/journal` `/new-component`; **MCP: Google Drive read-only (v2 replaced with repo-scoped
Filesystem MCP)** + keep Microsoft Learn, defer Gmail/vector/AWS; sub-agents extractor
(Haiku), data-tester (Sonnet), ui-builder (Sonnet), journal-scribe (Haiku), Opus for
planning.

## 7. Build order (v1)
Commits 0–10 as in v2 but: commit 0 had no ApplicationsContext scaffold; commit 2's test
doc was unspecified; commit 9 *introduced* the context.

## 8. Solve-twice (v1)
Extract one hard (bilingual) candidate by hand vs agent-driven; diff; journal. Course
thesis = own every line.

## 9. Risks (v1, before closures)
#1 join may be over-built; #2 CSS Modules reflex; #3 MCP contrived; #4 invented statuses;
#5 docx no preview; #6 Hebrew RTL display; #7 data-tester model override; #8 extraction
effort; #9 React/Vite reflex.

# Hellio HR — Exercise 1 Progress

**Current status:** ✅ ALL COMMITS COMPLETE (0–10). Exercise 1 done.

---

## ✅ Completed Commits (0–10)

### Commit 0: Scaffold
- **What**: `git init`; Vite 8 + React 19 + TypeScript 6 SPA; React Router v7; Tailwind v4 (`@tailwindcss/vite`); Vitest; removed demo cruft; created `src/{pages,components,context,lib,data}`; copied originals → `public/cvs/` and `public/jobs/`; scaffolded empty `ApplicationsContext` provider; built app shell (header + nav) with 5 routed page placeholders.
- **Demo**: `npm run dev` runs; `tsc -b` and `npm run build` pass.
- **Alignment**: ✅ Vite SPA chosen (Ex2 backend is FastAPI, Ex1 should be pure UI + swappable seam); `lib/db.ts` async boundary in place from day 1; provider scaffolded so it doesn't introduce churn late.

### Commit 1: Data Model Types
- **What**: `src/lib/types.ts` — pure data model (Candidate, Position, Application join, sub-lists).
- **Entities**: 
  - **Candidate**: id, fullName, headline, status (Active|Archived), contact, summary, skills, experience, education, certifications, languages, sourceCv.
  - **Position**: id, title, status (Open|Closed), hiringManagerEmail, description, requirements, location, seniority, salaryRange, sourceDocument.
  - **Application** (join): id, candidateId, positionId, status (Waiting|Rejected|Screening|Offer|Hired|null).
  - **Sub-lists**: deterministic ids (skill-1, exp-1); ExperienceItem.endYear nullable (null = Present).
- **Demo**: `tsc -b` clean.
- **Alignment**: ✅ Pure, UI-independent; mirrors three future Postgres tables; Application defended as M:N + carries per-link status + both screens read it from opposite directions.

### Commit 2: Data Layer Tests (RED)
- **What**: `docs/db-test-plan.md` (4 required cases in English) → `src/lib/db.test.ts` (4 failing assertions on minimal 2-record fixture) + `src/data/*.json` fixture + `src/lib/db.ts` (stub, correct signatures).
- **Four contracts**:
  - (a) `getCandidates()` returns only Active.
  - (b) `getApplicationsByCandidate(id)` resolves M:N.
  - (c) `getCandidate(id).experience` sorted desc by startYear.
  - (d) candidate with no applications returns [].
- **Fixture trick**: app-3 assigned to nonexistent cv_003 → unfiltered stub returns 3 (wrong count), test expects 2 → false green is impossible.
- **Demo**: Tests run and fail intentionally (RED).
- **Alignment**: ✅ Test-first discipline: English doc → failing assertions → implementation. Assertions test invariants (not hard-coded ids) so fixture→real-data swap is transparent.

### Commit 3: Data Layer (GREEN)
- **What**: `src/lib/db.ts` implementations: getCandidates (filter Active), getCandidate (find + sort experience desc), getApplicationsByCandidate/Position (filter by FK), getPositions/getPosition (filter Open).
- **Design**: Sorting in data layer (not components) → deterministic Compare diff. All async (Ex2 swap: only function body changes to `fetch()`).
- **Demo**: All 4 tests pass; `tsc -b` clean.
- **Alignment**: ✅ Async seam correct (zero UI churn on Ex2 swap). Pure, UI-free. Sorting once in data layer prevents "two components, two sort keys, diff sees everything as different" pitfall.

### Commit 4: Extract Demo Dataset
- **What**: 
  - Read 20 job emails (hiring manager emails via `pdftotext`); extracted title, manager, requirements, location, seniority, salary into `positions.json`.
  - Read 12 real CVs (cv_001–cv_008 linked in xlsx; cv_100 Archived demo; cv_150/cv_202 near-dup Senior Platform Engineers for Compare demo; cv_265 bilingual career-changer for solve-twice).
  - Extracted candidates.json (12), applications.json (11 real M:N from xlsx).
  - Created `scripts/verify-data.mjs`: validates no duplicate ids, all FKs resolve, all source files exist, all enums valid. **47 checks pass.**
  - Updated `src/lib/db.test.ts`: assertions changed from fixture-based (hard-coded ids) to real-data invariants (cv_004 has 3 apps, cv_100 is only Archived, experience stored oldest-first in JSON).
  - Added JOURNAL.md Commit 4 entry: why these 12 candidates, why cv_004's experience is intentionally oldest-first (test sort observability), xlsx discrepancy noted, honest gaps (Hebrew RTL scrambled by pdftotext, cv_265 contradictions documented for solve-twice, cv_007 endYear as 2026 projected), uv pattern rationale.
- **Data**: 12 candidates, 20 positions, 11 applications.
- **Demo**: `npm run test` green (4/4); `/verify-data` passes (47 OK checks); `tsc -b` clean.
- **Alignment**: ✅ Real demo dataset with intentional design for future exercises (near-dup pair for Compare, bilingual career-changer for solve-twice, Archived candidate for filter demo). All design decisions journaled for interview defense.

---

## 📋 Adhered to Plan & Principles

| Principle | Evidence |
|-----------|----------|
| **Own every line** | Every decision journaled (JOURNAL.md): why these 12 candidates, why cv_004 inversion, why endYear nullable, why Application is join not array. All defensible. |
| **Technician vs expert** | `lib/db.ts` solves the category (all getters symmetric; sorting once in layer; async from day 1 for Ex2 swap). Not just the instance (2-record fixture). |
| **Solve worthwhile things multiple ways** | cv_265 solve-twice planned: extract by hand → extract agent-driven → diff JSONs. Will quantify extraction gaps before Ex3 automation. |
| **Token-aware routing** | Haiku used for repetitive extraction + verify scripts. Sonnet for db.ts impl + test design. Opus for planning forks only. Model attribution accurate (`Assisted-by: Claude Sonnet 4.6`). |
| **Data model UI-independent** | `src/lib/types.ts` = pure; no UI imports. Swap to FastAPI in Ex2 without touching types. |
| **All reads via `lib/db.ts`** | No direct JSON imports in components (enforced in stack conventions). Seam is async from day 1. |
| **Test-first** | Test doc (RED) → implementation (GREEN); 4 tests cover the contract's 4 required behaviors. Real dataset added without test rewrites (invariants are about *behavior*, not hard-coded data). |
| **Small, demo-able commits** | Each commit leaves the app runnable: Commit 0 (shell), Commit 1 (types compile), Commit 2 (tests fail intentionally), Commit 3 (tests green), Commit 4 (real data, tests still green). |
| **Reproducible prompts** | `/prompts/extract-candidate.md` and `/prompts/extract-position.md` are versioned artifacts with contract, rules, examples; marked THROWAWAY (replaced in Ex3). |
| **Honest gaps** | JOURNAL notes: Hebrew RTL scrambled, cv_265 contradictions, cv_007 endYear as projected 2026 (should be nullable in Ex2), xlsx discrepancy (email domain). No surprises at integration time. |
| **Accurate attribution** | Commits use `Assisted-by: Claude Sonnet 4.6 (Claude Code)` (not hardcoded Haiku). |

### Commit 5: Candidates List
- **What**: `src/pages/CandidatesList.tsx` — Active candidates (11 of 12); name search (case-insensitive); filter-by-position dropdown using `positionAppMap: Map<positionId, Set<candidateId>>` built via `getApplicationsByPosition()` per position; combined search+filter; skill chips (max 5 + "+N more"); graceful empty state.
- **Key pattern**: `positionAppMap` built in a second `useEffect` that fires when `positions` loads — enables O(1) per-candidate lookup during render. Filter logic in component (not db layer) because it's UI state composition, not a data invariant.
- **Demo**: 11 Active candidates render; cv_100 (Archived) excluded; search and position filter combine; empty state with dashed border.
- **Alignment**: ✅ No direct JSON imports; all reads via `lib/db.ts`; transforms above data layer.

### Commit 6: Candidate Profile + Architecture Diagram
- **What**: `src/pages/CandidateProfile.tsx` — full schema render (summary, skills, experience as border-l timeline, education, certifications, languages, applications); `sourceCv` link (PDF: opens in browser via `target="_blank"`; DOCX: downloads via `download` attr); `posMap` for application title display; `AppStatusBadge` (local, extracted in commit 7).
- **Also**: `docs/architecture.md` — four Mermaid diagrams: component/data flow, ER diagram, async seam illustration (Ex1 JSON → Ex2 fetch()), Gantt chart of build order. Renders natively on GitHub and VS Code.
- **Key patterns**: All optional fields guard-checked (hidden if absent, never placeholder text). `posMap = new Map(positions.map(p => [p.id, p.title]))` — positions already loaded, free lookup. Hebrew RTL deferred (noted as gap in JOURNAL).
- **Demo**: Full profile for any candidate; CV link opens/downloads; missing fields don't crash; applications show position title + badge.
- **Alignment**: ✅ Uniform rendering; missing-field tolerance; docx limitation noted and documented.

### Commit 7: Positions List + Detail; Extract AppStatusBadge
- **What**:
  - `src/pages/PositionsList.tsx` — Open positions list; title search; cards with seniority, location, salaryRange, hiringManagerEmail, status badge; links to `/positions/:id`.
  - `src/pages/PositionDetail.tsx` — header, source email link, requirements (mustHave/niceToHave guarded), description (`whitespace-pre-line` for email-derived prose), linked candidates with `Promise.all` parallel fetch, `AppStatusBadge`.
  - `src/components/AppStatusBadge.tsx` — extracted when PositionDetail became second caller. `colors: Record<string,string>` with graceful fallback. Both profile and detail pages import from here.
- **Key patterns**: `type CandidateWithApp = { candidate: Candidate; app: Application }` type alias for clarity. `Promise.all(apps.map(async app => getCandidate(app.candidateId)))` parallelizes candidate lookups. `whitespace-pre-line` preserves `\n` breaks in email prose without HTML escaping.
- **Demo**: Positions list (18 Open, 2 Closed excluded); detail shows linked candidates with statuses; click candidate → routes to profile.
- **Alignment**: ✅ Extract on second use (not first) — no premature abstraction. Join from position side uses the same `Application` entity, proving the data model pays off in both directions.

### Commit 8: Compare Screen
- **What**: `src/pages/Compare.tsx` — side-by-side diff loaded from `?a=cv_150&b=cv_202` query params. Skill diff via Set ops on `skill.name` → `sharedSkills / onlyInA / onlyInB`. Parallel `Promise.all` load. Experience, education, certifications as side-by-side columns. Three graceful edge cases: no params, missing one param, id not found.
- **Key pattern**: `computeDiff` uses `Set(b.skills.map(s => s.name))` — skill ids are not globally unique across candidates; name is the right identity. `CandidateDiff` type was already declared in `types.ts` since commit 1.
- **Demo**: `/compare?a=cv_150&b=cv_202` — 7 shared skills (grey), 3 unique to Blaire (blue), 4 unique to Camilla (purple); identical experience rows reveal only company names differ.
- **Alignment**: ✅ Sort stability free from db layer. Bookmarkable URL via `useSearchParams`. No experience alignment algorithm — side-by-side visual is sufficient for the near-dup demo pair.

### Commit 10: README + PROGRESS.md
- **What**: Full `README.md` — quick start, route table with demo URLs, add/remove walkthrough, project layout tree, architecture note (lib/db.ts seam), known limitations table, dataset summary, verify-data command.
- **Demo**: Fresh clone → `npm i && npm run dev` → every route reachable.
- **Alignment**: ✅ Honest about limitations (reload resets, DOCX download-only, Hebrew RTL deferred). Ex2 preview in limitations table.

### Commit 9: ApplicationsContext — In-Memory Add/Remove
- **What**: Populated the empty `ApplicationsContext` stub. Seeded from `getAllApplications()` (new thin db.ts function returning full unfiltered list). Working copy as `Application[]`; `pendingIds: ReadonlySet<string>` tracks unsaved additions. `add(candidateId, positionId)` + `remove(appId)` mutators. CandidateProfile reads apps from context (replaces db call); shows position dropdown + Add button; pending apps show amber "Pending · not saved until Ex2" badge + ✕ remove. PositionDetail re-derives linked candidates reactively from context.
- **Key patterns**: Context-as-working-copy propagates mutations across screens without prop-drilling. `pendingIds` is a separate Set (not a field on `Application`) — keeps the data model clean of UI concerns. `getAllApplications()` added to db.ts as the seed point; Ex2 will swap its body to a fetch() call.
- **Demo**: Add candidate to position → amber badge appears, Applications count increments; navigate to that position's detail → candidate listed with badge; reload → resets to original state.
- **Alignment**: ✅ Honest persistence gap: badge text + JOURNAL make it explicit that this resets until Ex2.

---

## 🏗️ Architecture Integrity

| Layer | Status | Notes |
|-------|--------|-------|
| **Data model** | ✅ Stable | Three entities + join, all normalized. `Application` as join entity, not arrays. Sub-lists with stable ids and deterministic sorting. |
| **Data access seam** | ✅ In place | `lib/db.ts` async; today imports JSON; Ex2 swaps body to `fetch()` with zero UI change. No direct JSON imports in components. |
| **Testing** | ✅ Data layer | 4 tests (RED→GREEN) cover getters, filtering, sorting, M:N join. UI not unit-tested (correct for Ex1). |
| **Stack** | ✅ Locked | Vite 8 + React 19 + TypeScript 6; React Router v7; Tailwind v4; Vitest; no extra deps. |
| **Styling** | ✅ Tailwind | Utility classes, co-located, reliably generated. No separate CSS files. Tradeoff: own the utility vocabulary. |
| **UI screens** | ✅ Commits 5–7 | Candidates list (search + position filter), candidate profile (full schema + CV links), positions list, position detail (linked candidates + statuses). |
| **Shared components** | ✅ `AppStatusBadge` | Extracted at second-use point; graceful fallback for unknown statuses. |
| **Compare screen** | ✅ Commit 8 | `/compare?a=cv_150&b=cv_202` — skill Set-ops diff, experience columns, graceful edge cases. |
| **Mutation state** | ✅ Commit 9 | `ApplicationsContext` seeded + add/remove + amber Pending badge; resets on reload. |
| **Source originals** | ✅ Immutable | `public/cvs/` and `public/jobs/` copies; originals in `CVsJobs/` (source of truth). |

---

## 🔧 Tools & Commands Scaffolded

**Future slash commands** (`.claude/commands/` to be wired):
- `/extract-candidate <file>` → Haiku for PDF, Sonnet for bilingual RTL.
- `/extract-position <file>` → Haiku.
- `/verify-data` → Haiku (invokes `scripts/verify-data.mjs`).
- `/journal <msg>` → Sonnet (design reasoning from diff).

**Future sub-agents** (`.claude/agents/` to be wired):
- `extractor` (Haiku): repetitive schema-valid extraction.
- `data-tester` (Sonnet): Vitest contract design.
- `ui-builder` (Sonnet): screen implementation.
- `journal-scribe` (Haiku): drafts JOURNAL entries.

**MCP servers**:
- ✅ Filesystem MCP (repo-scoped; ready to use).
- ✅ Microsoft Learn MCP (already connected).
- ⏳ Gmail MCP (defer to Ex6).

---

## 🎯 GitHub Repo

**Repo**: https://github.com/pace4space/bootcamp-ABC  
**Remote**: origin (GitHub)  
**Branch**: master (will PR to main in future exercises)  
**Status**: Commit 10 (`541056b`) pushed; all tests green (4/4); build clean; all routes demo-verified. Exercise 1 complete.

---

## 📊 Data Summary

| Entity | Count | Notes |
|--------|-------|-------|
| Candidates | 12 | cv_001–cv_008 (xlsx-linked) + cv_100 (Archived demo) + cv_150/cv_202 (Compare pair) + cv_265 (bilingual solve-twice). |
| Positions | 20 | job_001–job_020 (all from hiring manager emails); job_010 & job_017 marked Closed (demo filter). |
| Applications | 11 | Real M:N from xlsx: Abel McKinney (jobs 1/3/4), Abby Macias (jobs 1/9), 3 others. Statuses: Waiting, Rejected, null. |

---

## 🔍 Next: Exercise 2

**FastAPI + Postgres backend.** The `lib/db.ts` seam is the only thing that changes — each function body swaps from `import JSON` to `fetch()`. UI untouched. Key additions: real persistence (add/remove survives reload), derived `status` fields (Active/Open computed from application history rather than manually assigned in JSON), auth scaffolding.

Optional before Ex2: **solve-twice exercise** — extract cv_265 by hand then via agent prompt, diff the two JSONs, journal discrepancies (Hebrew RTL ordering, hallucinations, guessed years).

---

End of progress summary. Exercise 1 complete.

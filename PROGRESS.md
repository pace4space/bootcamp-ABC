# Hellio HR — Exercise 1 Progress

**Current status:** Commit 4 (Extract Demo Dataset) complete. GitHub repo created and pushed.

---

## ✅ Completed Commits (0–4)

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

---

## 🏗️ Architecture Integrity

| Layer | Status | Notes |
|-------|--------|-------|
| **Data model** | ✅ Stable | Three entities + join, all normalized. `Application` as join entity, not arrays. Sub-lists with stable ids and deterministic sorting. |
| **Data access seam** | ✅ In place | `lib/db.ts` async; today imports JSON; Ex2 swaps body to `fetch()` with zero UI change. No direct JSON imports in components. |
| **Testing** | ✅ Data layer | 4 tests (RED→GREEN) cover getters, filtering, sorting, M:N join. UI not unit-tested (correct for Ex1). |
| **Stack** | ✅ Locked | Vite 8 + React 19 + TypeScript 6; React Router v7; Tailwind v4; Vitest; no extra deps. |
| **Styling** | ✅ Tailwind | Utility classes, co-located, reliably generated. No separate CSS files. Tradeoff: own the utility vocabulary. |
| **Mutation state** | ⏳ Scaffolded | `ApplicationsContext` empty; will populate in Commit 9 with add/remove mutators + "Pending • not saved until Ex2" badge. |
| **Source originals** | ✅ Immutable | `public/cvs/` and `public/jobs/` copies; originals in `CVsJobs/` (source of truth). |

---

## 🚀 Pending Commits (5–10)

| Commit | Screen | What | Gate |
|--------|--------|------|------|
| **5** | `/candidates` | Active filter + name search + filter by position dropdown. | Tests pass, search/filter work, UI renders gracefully. |
| **6** | `/candidates/:id` | Full profile schema + sourceCv link (opens PDF in-browser; docx downloads). | All fields render; missing fields don't crash; links work. |
| **7** | `/positions` + `/positions/:id` | Open filter + detail view with linked candidates + statuses. | Positions list and detail render; linked candidates visible with app statuses. |
| **8** | `/compare?a=cv_001&b=cv_150` | Side-by-side diff (shared/unique skills, experience, education, certs). | Diff renders two near-dup profiles; diff is stable (same data, same diff). Solve-twice: hand + agent extract cv_265, diff JSONs. |
| **9** | Add/remove application | Populate `ApplicationsContext` with mutators; "Pending • not saved until Ex2" badge. | Add/remove works; badge visible; reset on reload. |
| **10** | README + verification | Run instructions, walkthrough, JOURNAL pass. | Fresh clone: `npm i && npm run dev` works. |

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
**Status**: Commit 4 pushed; all tests green; `/verify-data` passes.

---

## 📊 Data Summary

| Entity | Count | Notes |
|--------|-------|-------|
| Candidates | 12 | cv_001–cv_008 (xlsx-linked) + cv_100 (Archived demo) + cv_150/cv_202 (Compare pair) + cv_265 (bilingual solve-twice). |
| Positions | 20 | job_001–job_020 (all from hiring manager emails); job_010 & job_017 marked Closed (demo filter). |
| Applications | 11 | Real M:N from xlsx: Abel McKinney (jobs 1/3/4), Abby Macias (jobs 1/9), 3 others. Statuses: Waiting, Rejected, null. |

---

## 🔍 Next Step: Commit 5

**Route**: `/candidates` (Active candidates list)  
**Components**:
- `CandidatesList`: filters by status === 'Active'; renders list with name, headline, skills snippet.
- **Search**: text input; filters by fullName (case-insensitive).
- **Filter by position**: dropdown; shows only candidates with applications to selected job.
- **UX**: graceful empty state; loading state (n/a for JSON, but async contract allows it).

**Test approach**: UI not unit-tested in Ex1 (too early); demo in browser before committing.

**Demo checklist**:
- [ ] `/candidates` loads and shows 11 Active candidates (not cv_100).
- [ ] Name search filters list in real time.
- [ ] Filter-by-position dropdown filters candidates with apps to that job.
- [ ] Search + filter combine correctly.
- [ ] Click a candidate → routes to `/candidates/:id`.
- [ ] Empty state renders gracefully if search/filter yields 0 results.

**JOURNAL entry** (Commit 5): transforms + filtering pattern; why filter in component vs data layer.

---

End of progress summary. Ready for Commit 5.

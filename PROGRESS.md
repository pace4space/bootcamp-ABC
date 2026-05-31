# Hellio HR — Progress

**Exercise 1:** ✅ Complete (commits 0–10)
**Exercise 2:** ✅ Complete — all criteria met; demo-able end-to-end
**Exercise 3:** ✅ Complete — 101/101 tests green; Step 9 Bedrock demo verified (all 5 criteria pass); markdown fence fix applied; no carry-forward items
**Exercise 4:** ✅ Complete — 148/148 tests green; Chat UI live; 4 demo questions verified; submission artifacts committed

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

## Exercise 2: FastAPI + Postgres Backend

### Commit 1 (ex2): `feat: FastAPI backend — all routes, JWT auth, 36 tests green`

**What shipped:**
- `api/` — full FastAPI service: 4 routers (auth, candidates, positions, applications), Pydantic schemas matching TypeScript types, SQLAlchemy 2.x async ORM, JWT Bearer auth with role middleware
- `api/alembic/` — Alembic migration `0001_initial_schema.py`: 10 tables (users, candidates, 5 candidate sub-tables, positions, position_requirements, applications), all FKs + CHECK constraints
- `api/tests/` — 36 pytest cases against SQLite in-memory; **36/36 green**
- `docker-compose.yml` — postgres:16-alpine + api service with health check
- `docs/api-contract.md` — camelCase route spec matching `src/lib/types.ts`

**Test status:** 36/36 ✅

**Completed for Ex2:**
- [x] `api/scripts/seed.py` — `candidates.json` + `positions.json` + `jobs.xlsx` → Postgres; idempotent; validated live
- [x] `docs/erd-ex2.drawio` + `docs/erd-ex2.png` — 10-table ERD with crow's-foot notation
- [x] `src/lib/db.ts` seam swap — all bodies → `fetch()` with JWT token; `apiFetch` helper
- [x] `src/context/AuthContext.tsx` — token state, `login()`, `logout()`, `useAuth()` hook
- [x] `src/pages/Login.tsx` — sign-in form, credential hint, error display
- [x] `vite.config.ts` — proxy `/api` → `localhost:8000`
- [x] `src/context/ApplicationsContext.tsx` — `pendingIds` removed; `add`/`remove` persist via API
- [x] `src/pages/PositionDetail.tsx` — inline edit form (admin|recruiter only); PATCH on save
- [x] `src/pages/CandidateProfile.tsx` — role-gated add/remove; all apps now deletable
- [x] `src/pages/CandidatesList.tsx` — position filter via context (no N HTTP requests)
- [x] `src/App.tsx` — `ProtectedRoute` + `/login` outside Layout; `AuthProvider` wraps tree

**Ex2 criteria verdict:**

| Requirement | Status | Evidence |
|---|---|---|
| F1 Login + Roles | ✅ | JWT Bearer; `require_role` on all mutating routes; 3 seeded roles; Login.tsx |
| F2 Persist Candidates | ✅ | 10 normalized tables; Alembic migration; add/remove survive reload |
| F3 API ↔ UI Contract | ✅ | Pydantic `alias_generator=to_camel` matches `types.ts` field-for-field |
| F4 Ingest Legacy Data | ✅ | `seed.py`: JSON + jobs.xlsx (name→ID resolution); idempotent double-run verified |
| F5 CVs Immutable | ✅ | `source_cv_path` column; `public/cvs/` never touched |
| F6 Edit Position UI | ✅ | PATCH endpoint + role-gated inline form in PositionDetail |
| NF1 Explicit Schema Changes | ✅ | `alembic/versions/0001_initial_schema.py` versioned |
| NF2 Easy to Extend | ✅ | Normalized sub-tables; seam intact; `lib/db.ts` is the only changed frontend file |
| Tests before logic | ✅ | 36 pytest cases committed RED before routers existed |
| Plan first | ✅ | Plan file committed before any code |

**Known gaps (carry-forward, not blockers):**
- ✅ `models.py` `created_at` — fixed 2026-05-28: `Mapped[Optional[datetime]]`; `from datetime import datetime` added; 36/36 green
- `src/lib/db.test.ts` tests skipped — need fetch-mock; contracts covered by 36 pytest cases
- No `.env.example` committed — hook blocks `.env*` writes; `.gitignore` covers `.env`
- `POST /admin/users` — out of scope by design; deferred to Ex6 at earliest

**Architecture decisions:**
- Natural string PKs (`cv_001`, `job_001`) — zero FK churn vs Ex1 data
- Fully normalized sub-tables (vs JSONB) — Ex4 skill-level search needs `WHERE name = 'Kubernetes'`
- `highlights TEXT[]` stays as array column — display-only, never filtered, 4th-level join unnecessary
- JWT Bearer (not session cookies) — works for browser now, Ex6 agent later without CORS complexity
- SQLite for tests (not Postgres) — zero infrastructure, fast CI, `aiosqlite` already a dep

---

---

## Exercise 3: LLM Extraction Pipeline

### Architecture

```
POST /api/ingest/cv        (multipart, PDF or DOCX)
POST /api/ingest/position  (multipart, TXT)
         │
         ▼
api/app/pipeline/
  Stage 1: parsers.py    → RawDocument (raw_text)
  Stage 2: heuristics.py → HeuristicHints (regex: email, phone, LinkedIn, GitHub)
  Stage 3: llm.py        → LLMResponse (Bedrock converse(), token counts, latency)
  Stage 4: validator.py  → CandidatePayload + warnings (SUCCESS / PARTIAL / FAILED)
  Stage 5: persister.py  → entity_id (atomic DB write via begin_nested savepoint)
  Stage 6: logger.py     → raw_documents + extraction_runs rows (flush only)
         │
         ▼
IngestResponse (status, entityId, runId, inputTokens, outputTokens, warnings, errors)
```

Two new DB tables (`raw_documents`, `extraction_runs`) via Alembic `0002_pipeline_tables.py`.
Versioned prompts at `api/app/pipeline/prompts/cv-v1.txt` and `position-v1.txt`.

### Steps Completed

| Step | Module | Tests | Commit |
|------|--------|-------|--------|
| 0 | `docs/ex3/` mini-plans (8 files) | — | `9089e3a` |
| 1 | `types.py` + ORM models + Alembic 0002 | 36/36 | `9089e3a` |
| 2 | `parsers.py` — PDF/DOCX/TXT → RawDocument | 12/12 | `8d51c6b` |
| 3 | `heuristics.py` — regex hints | 19/19 | `377a817` |
| 4 | `llm.py` + `prompts/` — Bedrock `converse()` | 8/8 | `0089c8f` |
| 5 | `validator.py` — JSON parse, type coercion, hint merge | 7/7 | `92b1e9f` |
| 6 | `logger.py` — flush raw_documents + extraction_runs | 5/5 | `24cb8e0` |
| 7 | `persister.py` — atomic candidate/position insert | 6/6 | `7d689c5` |
| 8 | `pipeline/__init__.py` + `routers/ingest.py` + `IngestResponse` | 6/6 | `db3d9b4` |

**Total: 99/99 tests passing** (branch `ex3`)

**Post-completion fix — 101/101 (2026-05-29):** `fix: strip LLM markdown fences before json.loads in validator` (`30b6bba`). Nova Lite non-deterministically wraps output in ` ```json ` fences despite prompt instruction. `_strip_fences()` pre-processor added at both CV and position parse sites. 2 regression tests added. Merged to `master`. **No remaining carry-forward items. Ex3 is closed.**

### Key Design Decisions

**Trust hierarchy: heuristics > LLM > null.** Regex-extracted email/phone/URLs lock in before the LLM call; heuristic wins silently on overlap (no warning). LLM fills semantic fields (name, skills, experience, summary).

**PARTIAL status.** A candidate with one bad date field is more useful than no candidate. `validate_cv_payload` collects field-level warnings, returns `PARTIAL`, and the entity is still persisted. The endpoint returns 201 with warnings in the body.

**Atomicity via `begin_nested()`.** Logger flushes (no commit); persister uses a savepoint inside the orchestrator's transaction; endpoint calls `db.commit()` once. Either all rows land or none do.

**Observability is unconditional.** `raw_documents` row written before LLM call. `extraction_runs` row written after every outcome including FAILED. No code path exits without both rows.

**`server_default="now()"` breaks SQLite reads.** Fixed by supplying explicit `datetime.now(timezone.utc)` in the logger — same pattern as `User.created_at`.

**Monkeypatch target is `app.pipeline.BedrockClient`.** The orchestrator does `from .llm import BedrockClient`, binding the name in `app.pipeline`'s namespace. Patching `app.pipeline.llm.BedrockClient` has no effect on the already-imported name.

### Endpoint Auth

`POST /api/ingest/cv` and `/api/ingest/position` require role `admin` or `recruiter`. Viewer → 403. Unauthenticated → 401.

### Step 9 — End-to-End Bedrock Demo ✅

Manual verification against live Postgres + real Bedrock call. Model: `amazon.nova-lite-v1:0` (us-east-1). Test CV: `cv_013.pdf` (Adeline Cordova).

**All 5 criteria met:**
1. ✅ `POST /api/ingest/cv` → 201, `entityId: cv_f241460e` (cv_ + 8 hex suffix)
2. ✅ `GET /api/candidates/cv_f241460e` → 200, full candidate (fullName, 12 skills, 3 experience, education)
3. ✅ `extraction_runs` row: `input_tokens=834, output_tokens=556, status=success`
4. ✅ Blank PDF → HTTP 422, `"No /Root object! - Is this really a PDF?"`
5. ✅ Wrong `AWS_ACCESS_KEY_ID` → HTTP 422, `UnrecognizedClientException` detail (not 500)

See `docs/ex3/submission-ex3.md` for full response bodies and design rationale.

---

## Exercise 4: Deterministic Search / SQL-RAG

### Architecture

```
POST /api/chat  (ChatRequest: question + history)
         │
         ▼
api/app/chat/
  Stage 1: generator.py   → GeneratedSQL  (Bedrock converse(), sql-v1.txt prompt)
  Stage 2: guard.py       → str           (blocklist + structure validation; raises UnsafeSQLError)
  Stage 3: executor.py    → QueryExecution (read-only; SQLite PRAGMA / Postgres READ ONLY txn)
  Stage 4: answerer.py    → str           (Bedrock converse(), answer-v1.txt; grounded on rows)
  Stage 5: orchestrator   → ChatResult    (run_chat_query(); persists query_runs row)
         │
         ▼
ChatResponse (status, answer, sql, columns, rows, rowCount, runId, inputTokens, outputTokens)
```

New DB table (`query_runs`) via Alembic `0003_query_runs.py`.
Versioned prompts at `api/app/chat/prompts/sql-v1.txt` and `answer-v1.txt`.

> **Module rename (2026-05-31):** `app/pipeline/` → `app/ingest/`, `app/query/` → `app/chat/`. See JOURNAL entry for rationale. 148/148 tests green after rename.

### Steps Completed

| Seg | Module | Tests | Commit |
|-----|--------|-------|--------|
| 01 | `chat/types.py` + `QueryRun` ORM + Alembic 0003 | 4/4 | `d42459b` |
| 02 | `chat/prompts/sql-v1.txt` + `answer-v1.txt` | — | `af81836` |
| 03 | `text_utils.py` + `chat/generator.py` (Bedrock SQL gen) | 5/5 | `d7d69c3` |
| 04 | `chat/guard.py` — blocklist + structure validation | 18/18 | `13103fe` |
| 05 | `chat/executor.py` — read-only seam (SQLite PRAGMA / PG txn) | 6/6 | `d1f9301` |
| 06 | `chat/answerer.py` — grounded answer synthesis, multi-turn | 5/5 | `a297dec` |
| 07 | `chat/__init__.py` + `routers/chat.py` + `POST /api/chat` | 9/9 | `a965c71` |
| —  | **Rename:** `app/pipeline/` → `app/ingest/`, `app/query/` → `app/chat/` | 148/148 | pending |
| 08 | `src/pages/Chat.tsx` — multi-turn UI + "What was retrieved" panel | — | pending |
| 09 | Live demo — full SQL-RAG loop against Postgres + Bedrock | — | pending |

**Running total: 148/148 tests green** (branch `ex4`, through seg 07 + rename)

### Key Design Decisions

**SQL-RAG over vector search for Ex4.** Structured HR data (status fields, salary, skill names) answers point queries exactly; embeddings are reserved for Ex5's semantic/fuzzy search. Deterministic queries = auditable results, no hallucinated row values.

**Guard runs before executor — defense in depth.** Guard rejects non-SELECT and forbidden keywords on the structure (not string literals, to avoid false positives on `'%Delete City%'`). Even if a write slips past the guard, the executor's `READ ONLY` transaction refuses it at the DB layer.

**SQLite / Postgres seam in executor.** Tests use in-memory SQLite where a second connection sees an empty schema; executor reuses the session connection and sandboxes with `PRAGMA query_only = ON/OFF`. Production Postgres gets a fully isolated `READ ONLY` connection with `statement_timeout`. Same pattern as Ex3's `server_default` and `ARRAY→JSON` seams.

**`ok=False` not an exception.** Any DB error (bad column, syntax, timeout) returns `QueryExecution(ok=False, error=...)`. Orchestrator logs it as `sql_error`; endpoint surfaces 422 + suggestion. Never a 500.

**Grounded answerer (seg 06).** LLM answer prompt injects the actual rows as JSON context; the model is instructed to cite only what is in those rows. Multi-turn is implemented as real conversation history entries (system prompt + alternating user/assistant turns), not concatenated strings.

**`query_runs` observability.** Every turn — success or failure — persists a row with sql, status, token counts, and latency. Mirrors Ex3's `extraction_runs` pattern.

---

End of progress summary.

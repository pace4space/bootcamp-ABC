# Hellio HR — Journal

---

## Ex3 Step 5 — validator.py, 7/7 tests passing

*2026-05-28*

### What shipped

**`api/app/pipeline/validator.py`** — Two public functions: `validate_cv_payload` and `validate_position_payload`. Both return a 3-tuple `(payload, warnings, ExtractionStatus)` and raise `ValidationError` on structural failures.

**`api/tests/pipeline/test_validator.py`** — 7 tests covering: valid JSON → SUCCESS; heuristic hint overrides LLM value silently; missing required field raises ValidationError; string year cast to int appends warning and returns PARTIAL; malformed JSON raises ValidationError.

### Design decisions

**ValidationError defined here, not in types.py.** It belongs to the validation stage. types.py is pure data contracts; error types are stage-local. If heuristics.py had its own errors, they'd live in heuristics.py.

**Why manual field-by-field validation instead of Pydantic?** Pydantic raises on first failure with no partial result. We want all fields extracted, with warnings for each coercion. "A candidate with 9/10 fields is more useful than no candidate" — `PARTIAL` status lets agents flag for human review rather than discarding the document.

**Heuristic override is a silent dict merge.** `{**llm_dict, **hint_overrides}` — hints win without emitting a warning because the override is intentional (regex is more reliable than LLM for structured contact info). Silencing it keeps warnings meaningful: every warning represents unexpected data quality degradation.

### Interview talking point

> Why distinguish PARTIAL from FAILED at the type level?

Because callers need to act differently. FAILED means "no entity created, safe to retry." PARTIAL means "entity created, review warnings before assigning to a position." Encoding this in `ExtractionStatus` makes it impossible to handle them the same way by mistake.

---

## SKILLability Infrastructure — Session-End Hook, Post-Commit Fix, gen-drawio Refinement

*2026-05-28*

### What shipped

**`api/app/models.py`** — `created_at` type corrected from `Mapped[Optional[str]]` to `Mapped[Optional[datetime]]` on `User` and `Application` models. Added `from datetime import datetime`. No runtime change (SQLAlchemy handles the column mapping); the annotation now reflects what Postgres actually stores. 36/36 tests green.

**`.claude/hooks/post-commit.sh`** — Path bug fixed. The hook lived at `.claude/hooks/post-commit.sh` symlinked to `.git/hooks/post-commit`. `$(dirname "$0")` resolved to `.git/hooks/`, so `$HOOK_DIR/../.skilllog` was writing to `.git/.skilllog` — not the intended `.claude/.skilllog`. Every commit since initial wiring was silently logging to the wrong file. Fix: `git rev-parse --show-toplevel` returns the repo root regardless of invocation context.

**`.claude/hooks/session-end.sh`** (new) — Runs on Claude's `Stop` event. Auto-fills `## Commits This Session` in today's session note from `git log --oneline --after=TODAY`. Emits a terminal reminder if Key Learnings still has template placeholder text. Wired in `.claude/settings.json` under the `Stop` hook event.

**`.claude/skills/gen-drawio/SKILL.md`** — Two additions:
1. *Canvas sizing algorithm*: measure content bounding box, add 20% margin, round up to nearest 100px, pick the smallest preset that fits. Never default to Extra Large (3600×2400) — exports with vast white borders when content is small.
2. *Learnings*: parallel arrow corridor rule (n×20px minimum, size before placing tables); canvas oversizing anti-pattern (fit to content, not to the largest preset).

**Memory** — `feedback_docker_user_flag.md` added to project memory: always pass `--user "$(id -u):$(id -g)"` on any `docker run` that writes to a host-mounted volume. Directly relevant to Ex3 if the extraction pipeline shells out to a containerised tool.

---

### session-end.sh audit — tail-overwrite bug caught immediately

The first implementation of session-end.sh replaced everything from `## Commits This Session` to end of file. This is a destructive tail-overwrite: any section added after commits in the future would be silently deleted on every Stop event.

The correct approach: locate the section body (line after header to next `\n##` or EOF), replace only that span, leave the rest of the file untouched. One additional subtlety: `body_end` must point to the `\n` before the next section header — not past it — so inter-section blank lines are preserved.

```python
next_section = re.search(r'\n## ', content[body_start:])
body_end = body_start + next_section.start() if next_section else len(content)
new_content = content[:body_start] + commits + '\n' + content[body_end:]
```

The `+1` variant (which the first implementation used) consumes the `\n` separator and collapses blank lines between sections. The lesson: section replacement in structured markdown requires finding both edges — start AND end of body — not just truncating from the header.

---

### post-commit hook path lesson

Git hooks invoked via symlink resolve `$(dirname "$0")` to the symlink's location (`.git/hooks/`), not the target file's location (`.claude/hooks/`). Any path constructed from `$HOOK_DIR` was therefore rooted in the wrong directory. The silent failure mode — no error, just wrong file — is the worst kind: `.git/.skilllog` grew normally, so nothing looked broken. Only a direct inspection revealed the misrouting.

Rule going forward: git hook scripts that need to reference the repo root should always use `git rev-parse --show-toplevel`. Never `dirname`-relative paths in git hooks.

---

## Exercise 2, Commit 3 — Seed Script + Live Postgres Validation

*2026-05-27*

### What shipped

`api/scripts/seed.py`: reads `candidates.json` + `positions.json` + `jobs.xlsx` (openpyxl), resolves Excel candidate names → IDs via a lookup dict built during candidate insert, inserts all rows idempotently. Validated against live Postgres: 3 users, 12 candidates, 20 positions, 11 applications, all sub-tables. Second run: all 0.

---

### The sub-table idempotency trap

`ON CONFLICT DO NOTHING` is only effective when there's a unique constraint to trigger. Child tables like `candidate_skills` have a SERIAL primary key — every insert gets a fresh auto-incremented id, so there is nothing to conflict on. Running seed twice doubled all sub-table rows (116 → 232 skills, 26 → 52 experience entries).

Fix: the parent row insert returns a rowcount. If it's 0, the parent already existed — skip all its child inserts. One flag per entity, zero extra queries.

```python
n = await _upsert(session, "candidates", [row], "id")
if n == 0:
    continue  # already seeded — skip sub-tables
```

This pattern generalises to any seed script that has parent/child relationships without a composite unique key on the child. The failure mode is silent (no error, just doubled data), which makes it worse than a loud crash.

---

### Docker validation was clean

First real Postgres run required zero fixes — the SQLite compatibility patches in `conftest.py` (ARRAY→JSON, explicit `created_at`, no pool args) were correct prophylactically. The live stack also confirmed: 11 Active candidates (1 Archived excluded), 18 Open positions (2 Closed excluded), applications shape matches TypeScript contract exactly.

---

## Exercise 2, Commit 1 — FastAPI Backend: All Routes, 36/36 Tests Green

*2026-05-27*

### What shipped

A complete FastAPI backend in a single commit: 10-table Alembic migration, JWT auth with role middleware, four routers (auth, candidates, positions, applications), Pydantic schemas that mirror `src/lib/types.ts` exactly, and 36 pytest cases against SQLite in-memory — all green.

---

### The seam pays off

The Ex1 discipline of async-from-day-1 in `lib/db.ts` meant the backend shape was pre-determined. Pydantic schemas were defined by simply reading `types.ts` and translating field by field. Camelcase serialisation via `alias_generator=to_camel` in Pydantic v2 handles the Python ↔ TypeScript naming gap without manual field aliases. The lesson: data contract first, implementations second — and the contract was already written in Ex1.

---

### Schema decisions I'd defend

**Natural string PKs (`cv_001`, `job_001`)** over UUID auto-generation. The cost is a longer PK column; the benefit is zero FK churn when migrating the seeded JSON into Postgres, and human-readable ids that survive `psql` debugging sessions without UUIDs to copy-paste. UUIDs deferred to Ex3+ where new records are created from documents (not migrated from files).

**Fully normalized sub-tables** over JSONB arrays for skills, experience, education, certifications, languages. Argued in CLAUDE.md since Ex1: Ex4 needs `WHERE skill.name = 'Kubernetes'` — JSONB blocks indexing that. The cost is 5 extra tables and a `selectinload` chain per candidate fetch; the benefit is query-ready structure from day one. No regrets when `_to_schema()` had to manually traverse them — that's the right place to pay the cost.

**`highlights TEXT[]` as a Postgres array column** — deliberate exception to the normalization rule. Highlights are display prose, never filtered or searched. A `candidate_experience_highlights` table with a FK would be a 4th-level join for no query benefit. The tradeoff: tests need a SQLite compatibility shim (`ARRAY(Text)` → `JSON()`). Worth it.

**`UNIQUE(candidate_id, position_id)` on applications** — the duplicate-application guard lives at the DB level, not just in the router. The router catches `IntegrityError` and re-raises as 409. Defense in depth: even if the router logic is bypassed (e.g. direct SQL, future bulk import), the constraint holds.

---

### Test-first, honestly

The test plan was written before any router existed. 30 of 36 tests were RED when first committed — the 6 that passed were either the health endpoint or coincidental 404s (unregistered routes returning 404 happened to satisfy `test_*_returns_404` assertions). That's the expected shape of a RED test suite: structure is correct, contracts are specified, implementation is absent.

The SQLite compatibility layer in `conftest.py` required three explicit patches:
1. `ARRAY(Text)` → `JSON()` on `CandidateExperience.highlights` before `create_all`
2. Own engine without `pool_size`/`max_overflow` (SQLite rejects those kwargs)
3. Explicit `created_at=datetime.now(timezone.utc)` everywhere — SQLite stores the literal string `"now()"` instead of executing the Postgres server-default function, then crashes trying to parse it as a datetime on read-back

Patch 3 surfaced as the only post-implementation failure: `test_post_creates_201` and `test_post_persists` both hit `ValueError: Invalid isoformat string: 'now()'` on `db.refresh(app)`. One-line fix in `applications.py`. The lesson: Postgres server defaults are invisible during development but visible the moment SQLite sees them. The conftest seed rows already did this correctly (the agent that wrote conftest.py knew to supply `created_at=_NOW`). The router didn't. Asymmetry between test infrastructure and production code is a failure mode worth watching.

---

### Agent workflow learnings

This session surfaced two compounding failure modes when spawning subagents, now captured in memory (`feedback_subagent-plan-mode-bleed.md`):

**Plan-mode bleed.** Agents spawned while the parent is in plan mode inherit the "no edits" constraint. They produce complete correct output in response text, then say "plan mode prevented execution." The parent must re-extract and write manually — double tokens, same files. Fix: `ExitPlanMode` before spawning any writing agent. Open every writing-agent prompt with an explicit EXECUTION declaration.

**Model routing for documentation.** TEST-PLAN.md is a transformation task: read a spec, produce structured markdown. That is Haiku territory. It was routed to Sonnet and spawned as an agent — ~29K tokens, ~2 minutes, and the file never landed. The same file written inline from current context: ~2 seconds. The compound failure: wrong model + plan-mode bleed = highest-cost outcome. Rule going forward: if the output is deterministic given the inputs (spec → markdown, JSON → SQL), write it inline or Haiku. If it requires judgment about correctness, Sonnet. Architecture or cross-cutting design, Opus (≤2/session).

The 21-minute perceived "hang" on Agent 3 was actually `pip install -r requirements.txt` building the venv — not stuck pytest. Actual test execution: 88 seconds (bcrypt hashing 3 users × 36 function-scoped fixtures). Lesson: when an agent appears stuck, check `htop` for the actual process before killing. The evidence was in the process list: `pytest tests/ -q --tb=no` running actively.

---

### What I'd change

**The `created_at` column type** in `models.py` is `Mapped[Optional[str]]` — wrong. It should be `Mapped[Optional[datetime]]`. The agent that wrote it typed the annotation as str (probably copying from the TIMESTAMP column type name). This won't cause Postgres issues (SQLAlchemy handles the datetime ↔ db conversion) but it's misleading. Refactor candidate for a later cleanup commit.

**Auth before candidates** in the commit order. The original plan placed auth at commit 6 (after all GET routes). But `get_current_user` is in `app/auth.py` (not the auth router), and all tests generate tokens via `create_access_token` directly — so the commit order didn't actually block tests. It worked out, but the mental model was confused. Cleaner sequence: auth router first so the login endpoint and token validation are both live before any CRUD routes. Noted for Ex3+.

---

## Exercise 1 Journal

---

## Commit 9 — Operation SKILLability: Learning Infrastructure

Established a closed-loop learning system inside `.claude/` that grows from use without requiring manual intervention.

**What shipped:**
- `CLAUDE.md` updated with SKILLability charter: principles, agentic commands, hooks, skill discipline (naming conventions, Learnings section requirement), and Hermes migration path
- 5 skills: `commit-correct-attribution`, `model-routing-cost-aware`, `verify-before-complete`, `session-synthesize`, `gen-drawio`
- 3 agentic commands (`.claude/commands/`): `memory-synthesize`, `skill-new`, `session-synthesize` — Claude invokes these proactively on triggers, no user prompting needed
- 2 bash hooks: `session-start.sh` (UserPromptSubmit, once-per-day guard) + `post-commit.sh` (git hook, logs to .skilllog, signals at commit 5 cadence)
- `.skilllog` JSONL trajectory log — accumulates errors and events; fuel for Hermes autonomous learning in Ex5+
- `ASSESSMENT.md` — 10-section analysis of Claude Code vs Hermes Harness, three integration paths

**Why this now.** Ex1 is the last exercise without an LLM pipeline. Once Ex2 introduces FastAPI + extraction, failures will start accumulating. The learning infrastructure needs to be in place *before* the failures happen, not after — otherwise the signal is lost.

**The design decision: hooks over commands.** First draft had 6 user-invoked commands. Rejected. Every workflow step that can be automatic should be automatic; commands are escape hatches, not the required path. The `session-synthesize` command exists so the user *can* call it, but Claude calls it proactively at session end.

**Verify-before-complete principle.** The previous session declared "Phase 1 complete" when `.claude/commands/` didn't exist and no hooks were wired. Added "Verify before declaring done" as a non-negotiable principle to CLAUDE.md and captured the failure mode in the `verify-before-complete` skill. Designed ≠ Done.

**gen-drawio skill.** Sourced from `.tmpclaude/drawio/skill.MD` (existing draft). Promoted to proper skill with naming convention (`gen-*` prefix), missing `## Purpose`, `## When to Use`, and `## Learnings` sections added. Trigger phrases in `## When to Use` make it spontaneously invocable on "diagram", "visualize", "map out".

**Path to Hermes (Ex5+).** The data structures built here map directly to Hermes: `.claude/skills/` → Hermes skill library; `.skilllog` → trajectory log for RL training; `session-notes/` → cross-session recall; `MEMORY.md` → Hermes memory system. No rework needed at migration time.

---

## Commit 10 — ApplicationsContext: In-Memory Add/Remove

**What changed.** Populated the `ApplicationsContext` stub (scaffolded empty in commit 0). Context now seeds from `getAllApplications()` on mount, holds a working copy as `Application[]`, exposes `add(candidateId, positionId)`, `remove(appId)`, and `pendingIds: ReadonlySet<string>`. CandidateProfile reads applications from context instead of the db function; PositionDetail re-derives linked candidates reactively from context. Both show an amber "Pending · not saved until Ex2" badge on unsaved additions.

**Why context is the right primitive here.** The mutation (add/remove) needs to be visible from two screens simultaneously: add a candidate to a position from CandidateProfile, navigate to PositionDetail, see them already listed. Context propagates this without prop-drilling or a server round-trip. The alternative — keeping db as the source and passing a local state delta down — would require every read site to merge two sources. Context-as-working-copy is cleaner.

**The seam distinction.** `getAllApplications()` was added to `db.ts` to give the context a single seed point. The existing `getApplicationsByCandidate` and `getApplicationsByPosition` functions still exist — they're the Ex2 swap seam. In Ex2, the context will seed from a real API call and the mutators will call POST/DELETE endpoints. The UI won't change.

**Why `pendingIds` is a Set of ids, not a boolean flag on Application.** The `Application` type is a pure data model (Ex2 Postgres row); polluting it with a UI concept like `isPending` would leak UI state into the data layer. A separate `Set<string>` in the context carries that concern without touching the model.

**The honest gap.** Reload resets everything — the working copy is re-seeded from the static JSON. This is documented in the badge text ("not saved until Ex2") and in the plan. No surprises at integration time.

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

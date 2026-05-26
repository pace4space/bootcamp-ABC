# Hellio HR — Exercise 1: Candidate Profile Viewer & Diff — Plan (v2)

## Changelog (v1 → v2) — your four approved amendments

1. **Join entity accepted.** Risk #1 **closed** — `Application` ships as a normalized
   entity, no further debate.
2. **`ApplicationsContext` scaffolded empty in commit 0**, then populated with real
   add/remove behavior in commit 9 (not introduced for the first time in 9).
3. **MCP: drop Google Drive; wire Filesystem MCP scoped to the repo** instead.
   Risk #3 **closed**.
4. **Explicit `status` field on Candidate and Position**, assigned manually in JSON,
   JOURNAL-noted as *"will be derived by the backend in Ex2."* Risk #4 **closed**.
5. **Test document precedes commit 2's test file** and must cover, at minimum:
   (a) `getCandidates` returns only `Active`; (b) `getApplicationsByCandidate` resolves
   M:N correctly; (c) `experience` sorts descending by `startYear`; (d) a candidate with
   no applications returns `[]` gracefully. **Tests must fail before implementation.**
6. **Styling: Tailwind CSS** (not CSS Modules). Risk #2 **closed** — utility classes are
   self-contained, co-located, and reliably Claude-generated; the cost (owning the
   utility vocab) is accepted.

*v1 is preserved verbatim in the Appendix at the bottom of this file. Commit 0's first
action splits these into `docs/plan-v1.md` and `docs/plan-v2.md` in the repo.*

---

## Context

First of 8 exercises building toward an agentic HR system. Ex1 is a **UI-only,
JSON-backed** candidate/position viewer with side-by-side diff. No DB, no auth,
no LLM in the running app — those arrive later. The point of Ex1: (a) a **data model +
UI seam** clean enough to live with through Ex8 (FastAPI Ex2, LLM extraction Ex3, search
Ex4, embeddings Ex5, agent Ex6), and (b) practice **Claude Code agent use** (CLAUDE.md,
slash commands, MCP, sub-agents) with deliberate model routing.

Decisions: **Vite + React + TS SPA**; reads behind one async `lib/db.ts` seam (swap
internals → FastAPI in Ex2, UI untouched); add/remove position is **in-memory only**
with a "not saved until Ex2" badge; demo dataset = **~12 candidates + all 20 positions**.

---

## 1. Data exploration findings (verified by reading the files)

- **270 CVs** (`cv_001`–`cv_270`): **216 PDF + 54 DOCX**. Consistent schema across
  formats: name, headline, contact (phone `060-…`, email, Israeli city, LinkedIn,
  GitHub), summary, skills, experience (`Company NNN` + city + year range + bullets),
  education, certifications, languages-with-proficiency.
- **Synthetic + templated**: many near-duplicate profiles (cv_100/150/202 share an
  almost identical "Senior Platform Engineer" summary) → **good diff pairs**.
- **Bilingual Hebrew/English** CVs (e.g. `cv_265`, a sales→DevOps career changer):
  English headers/skills, **Hebrew RTL bullets**. `pdftotext` scrambles RTL →
  extraction uses a multimodal model on the original, not extracted text (§5).
- **20 positions** = hiring-manager **emails** (From/To/Subject + prose), not structured
  specs. Requirements buried in prose; salary/location/seniority sometimes present.
- **`jobs.xlsx` is the JOIN TABLE**: `Job # · Title · Hiring Manager (email) ·
  Description File · (Candidate N, Status N)×10`. Gives normalized title, manager email,
  and candidate↔job links with a **per-link status** (`Waiting`/`Rejected`/blank). Only
  jobs **1–4, 9** have linked candidates. **Linked by NAME, not cv_id** → mapping needs
  reading CVs. Abel McKinney → jobs 1/3/4 confirms **many-to-many**.

**Key shape:** relationship `status` (Waiting/Rejected) is a property of the *pair*;
candidate-level "Active" and position-level "Open" (the brief's filters) **don't exist
in the data** — assigned manually (Amendment 4, §5).

---

## 2. Data model

Three entities + one join → `data/candidates.json`, `data/positions.json`,
`data/applications.json` (mirroring three future DB tables). Types in `lib/types.ts`
(pure, UI-independent). Stable IDs from filenames (`cv_001`, `job_001`).

**Candidate** — list/profile/diff; extended Ex2 (DB row), Ex3 (agent fields), Ex5 (embeddings).
| field | read by | future |
|---|---|---|
| `id` (`"cv_001"`) | everything (key) | Ex2 PK |
| `fullName` | list, search, profile, diff; links to xlsx | Ex2 |
| `headline` | list subtitle, profile, diff | Ex3 regen |
| `status: "Active"\|"Archived"` | candidate list **filter** — **manual in JSON, derived by backend in Ex2** | Ex2 |
| `contact {email,phone,city,linkedinUrl,githubUrl}` | profile | email = Ex2 unique key; Ex6 contact |
| `summary` | profile, diff | Ex3 regen, Ex5 embed |
| `skills: Skill[]` | profile, **diff core**, search | Ex4 match, Ex5 embed |
| `experience: ExperienceItem[]` | profile, diff (sort `startYear` desc) | Ex4 |
| `education: EducationItem[]` | profile, diff | Ex4 |
| `certifications: Certification[]` | profile, diff | Ex4 |
| `languages: Language[]` | profile | — |
| `sourceCv {fileName,format,path}` | "link/preview original" req | Ex3 ingests |

Sub-lists with **stable ids + clear sorting**: `Skill{id,name}` (sort alpha; diff = set
ops on `name`), `ExperienceItem{id,role,company,location?,startYear,endYear|null,
highlights[]}` (sort `startYear` desc; `null` end = Present), `EducationItem{id,degree,
institution,startYear,endYear}`, `Certification{id,name,year}`,
`Language{id,name,proficiency}`.

**Position** — list/detail + candidate "add to position"; extended Ex2, Ex4.
`id("job_001")`, `title` (normalized from xlsx), `status: "Open"|"Closed"` (**manual in
JSON, derived by backend in Ex2**), `hiringManagerEmail` (Ex6 = who the agent emails),
`description`, `requirements{mustHave[],niceToHave[]}?`, `location?/seniority?/
salaryRange?`, `sourceDocument{fileName}` (original email, unchanged).

**Application** — the JOIN (**accepted, Risk #1 closed**). Read by both screens, written
by add/remove. `id`, `candidateId` (FK), `positionId` (FK), `status:
"Waiting"|"Rejected"|…`. Extended Ex6 (agent proposes status, human approves).

**Why a join entity:** (1) genuine **M:N** in the data; (2) the relationship carries its
own attribute (`status` is "this candidate *for this position*"); (3) both screens read
it from opposite directions — one normalized list, no drift; (4) Ex2 = Postgres join
table, Ex6 = agent acts on applications. Grounded in the xlsx, not speculative.

---

## 3. Stack (Vite + React + TypeScript SPA)

- **Vite SPA + typed async seam:** backend belongs to Ex2. Ex1 = pure UI + one
  swappable module. `lib/db.ts` exposes `async` getters that today `import` JSON; Ex2
  swaps only their bodies to `fetch()` FastAPI — **zero UI change, no throwaway server
  code**.
- **TypeScript** = compile-time "consistent schema"; guards the pitfall *"hard-coding
  profile shape"* (UI reads only declared fields; optionals nullable + tolerated).
- **React Router**; **Tailwind CSS** (utility classes co-locate style with markup → one
  component audited in one place, no JSX↔CSS class drift, reliably generated by Claude
  Code; the tradeoff: utility vocab is a line you must still own); **React built-in
  state** (no Redux); **Vitest** for the data layer.
- **Rejected — Next.js (App Router):** server/client split + App Router conventions +
  route-handler code that Ex2's FastAPI makes throwaway. SPA swap-seam wins.

---

## 4. Screen / route breakdown

Reads via `lib/db.ts`; writes via `ApplicationsContext` (in-memory).

| route | reads | writes |
|---|---|---|
| `/` → `/candidates` | — | — |
| `/candidates` | `getCandidates()` `status==="Active"`; search by name + filter by position | — |
| `/candidates/:id` | `getCandidate(id)`, `getApplicationsByCandidate(id)`, `sourceCv` link | add/remove application (in-memory) |
| `/compare?a=cv_001&b=cv_017` | two candidates; diff (shared/unique skills, experience) | — |
| `/positions` | `getPositions()` `status==="Open"` | — |
| `/positions/:id` | `getPosition(id)`, `getApplicationsByPosition(id)`, description, requirements | — |

- **Original CVs:** copies in `public/cvs/` (copied, never edited). PDF opens in-browser;
  **docx → download link** (no native preview — Risk #5).
- **Mutation honesty (in-memory):** `ApplicationsContext` (scaffolded empty in commit 0,
  real behavior in commit 9) seeds from `applications.json`, holds a working copy.
  Add/remove mutate state only, show **"Pending • not saved until Ex2"**, **reset on
  reload**. **FLAG: Context provider — ask me to explain before commit 9.**
- Compare uses **query params** (bookmarkable). **FLAG if you want it explained.**

---

## 5. CV/Job → JSON pipeline (throwaway, Ex1-only)

Prompts = **versioned artifacts in `/prompts/`**, header `THROWAWAY — Ex1 only; replaced
by the real pipeline in Ex3`. Files: `prompts/extract-candidate.md`,
`prompts/extract-position.md`, `prompts/README.md`.

**Strategy:** (1) paste exact `lib/types.ts` as the output contract; (2) one worked
example; (3) rules — don't invent fields, unknown optionals → `null`, preserve original-
language strings, deterministic sub-ids (`skill-1`), JSON only; (4) **bilingual CVs →
multimodal model on the original PDF** (RTL scrambles under text extraction).

**Volume:** all **20 positions** (cheap; xlsx gives title/manager/links deterministically)
+ **~12 candidates** = ~9 names linked in `jobs.xlsx` (real join + statuses) + 2–3
near-dup Platform Engineers (diff demo) + 1 bilingual/career-changer (schema stress).

**Honest gaps:**
- **Name → cv_id mapping:** `grep` CV text for the 9 sheet names; documented in JOURNAL.
- **`status` fields are assigned manually** in JSON (Amendment 4): default `Active`/`Open`,
  a couple `Archived`/`Closed` for demo. JOURNAL notes *"will be derived by the backend
  in Ex2."* Risk #4 closed.

---

## 6. Claude Code agent setup

### CLAUDE.md (actual content)
Project + 8-exercise arc; your principles (own every line / technician-vs-expert /
solve-twice / token-aware routing); architecture rules (pure UI-independent data model;
**never mix UI with data transformation**; all reads through `lib/db.ts`; `public/cvs/`
immutable); stack conventions (Vite+React+TS, Router, CSS Modules, hooks; **no new dep
without asking**; Tailwind for styling — no separate CSS files); schema discipline (optionals nullable, tolerate missing); git (commit
every working step); testing (`lib/db.ts` test-first; UI not unit-tested in Ex1); prompts
are `/prompts/` artifacts; JOURNAL.md one entry per commit; model-routing policy.

### Slash commands (`.claude/commands/`)
| command | does | model + why |
|---|---|---|
| `/extract-candidate <file>` | run throwaway prompt → schema-valid Candidate JSON | **Haiku**; bilingual → **Sonnet** (RTL/multimodal) |
| `/extract-position <file>` | same for a position email | **Haiku** (clean text) |
| `/verify-data` | validate JSON vs types; every FK resolves; every `sourceCv.path` exists | **Haiku** (invokes a script) |
| `/journal <msg>` | scaffold JOURNAL entry (what/why/alternatives/defense) from the diff | **Sonnet** (design reasoning = interview value) |
| `/new-component <Name>` *(optional)* | scaffold a Tailwind-styled component | **Haiku** (boilerplate) |

### MCP servers
- **Wire now: Filesystem MCP scoped to the repo** (Amendment 3) — practices the "MCP to
  access external data" objective against repo files (source docs, JSON), repo-scoped so
  it can't reach outside. Risk #3 closed.
- **Keep:** Microsoft Learn MCP (already connected; zero-cost docs lookups).
- **Defer:** Gmail → Ex6; vector store → Ex5; AWS → Ex8.

### Sub-agents (`.claude/agents/`)
- **extractor (Haiku):** context = types + extraction prompt + **one** file. Cheap,
  no leakage, repetitive structured extraction.
- **data-tester (Sonnet):** context = `lib/db.ts` spec + types + test doc. Designs the
  Vitest contract (edge cases). *Overrides your "Haiku for pure-fn tests" rule for
  contract design; rote cases can drop to Haiku — Risk #7.*
- **ui-builder (Sonnet):** context = conventions + one screen spec + types. Module impl.
- **journal-scribe (Haiku):** context = diff + template; drafts, you edit. `/journal`
  invokes it.
- **Opus:** not a standing agent — planning + doubt resolution only.

---

## 7. Build order (commit-by-commit, each demo-able)

JOURNAL prompt per commit in *italics*.

0. **`chore: scaffold`** — `git init`; split this plan into `docs/plan-v1.md` +
   `docs/plan-v2.md`; Vite+React+TS, Router, Tailwind, `.gitignore`, CLAUDE.md,
   `/prompts/` stubs, copy originals → `public/cvs/`; **scaffold `ApplicationsContext` as
   an empty provider wrapping the app** (no behavior yet). *Demo: app shell + nav runs,
   provider mounted.* *JOURNAL: why Vite-SPA over Next; the `lib/db.ts` seam; why the
   provider exists from day 1.*
1. **`feat: types`** — `lib/types.ts` (entities + sub-lists). *Demo: `tsc` clean.*
   *JOURNAL: the Application join entity; per-field screen+future justification.*
2. **`test: data layer (RED)`** — `docs/db-test-plan.md` first, covering at least
   **(a)** `getCandidates` returns only Active, **(b)** `getApplicationsByCandidate`
   resolves M:N, **(c)** `experience` sorts desc by `startYear`, **(d)** candidate with no
   applications → `[]`. Then `lib/db.test.ts`, **failing**. *Demo: tests run, fail
   intentionally.* *JOURNAL: test-first rationale; the contract the tests encode.*
3. **`feat: data layer (GREEN)`** — `lib/db.ts` async getters/finders; tests pass on a
   fixture. *Demo: green.* *JOURNAL: the async seam; pure & UI-free.*
4. **`chore: extract dataset`** — `/extract-*` → `data/*.json` (~12 + 20 + real links);
   `/verify-data` passes. *Demo: db.ts returns real data.* *JOURNAL: prompt design;
   name↔cv_id mapping; manual status fields ("derived in Ex2"); throwaway nature.*
5. **`feat: candidates list`** — `/candidates` Active filter + search + filter by
   position. *Demo: browse/filter.* *JOURNAL: transforms out of components.*
6. **`feat: candidate profile`** — `/candidates/:id` full schema + `sourceCv` link.
   *Demo: view, open original.* *JOURNAL: uniform rendering; missing-field tolerance;
   docx limitation.*
7. **`feat: positions`** — `/positions` (Open) + `/positions/:id` (description + current
   candidates + statuses). *Demo: browse, see linked candidates.* *JOURNAL: join from
   the position side; title vs subject.*
8. **`feat: compare`** — `/compare?a=&b=` diff. *Demo: two near-dup Platform Engineers.*
   *JOURNAL: diff algorithm; stable ids+sorting make it trivial.*
9. **`feat: add/remove position (in-memory)`** — **populate the existing
   `ApplicationsContext`** with mutators + "Pending • not saved (Ex2)" badge. *Demo:
   add/remove, badge, resets on reload.* *JOURNAL: the Context pattern (FLAG); the
   honest persistence gap.*
10. **`docs: README + demo script`** — run instructions, walkthrough, JOURNAL pass.
    *Demo: fresh clone → `npm i && npm run dev`.* *JOURNAL: retrospective; what Ex2 changes.*

**Patterns to explain before coding:** `ApplicationsContext` provider (0 scaffold / 9
behavior); **async** `lib/db.ts` over local JSON (why async now → zero-change Ex2 swap,
commit 3); query-param compare route (8); any clever diff types (8).

---

## 8. "Solve it more than one way" candidate

**Extract ONE hard candidate twice — by hand, then agent-driven — and diff the JSONs.**
Pick the bilingual/career-changer CV (Hebrew RTL + non-DevOps titles). By hand: read the
PDF, type the JSON. Agent: multimodal → JSON via the throwaway prompt. Compare:
hallucinations, mis-ordered Hebrew, invented skills, guessed years — journal each.

**Why this one:** extraction is the course's thesis — *own every line; unowned agent
output is worthless*. Doing it by hand makes you feel what the agent does and where it's
wrong, so you own the schema as a contract **before Ex3 automates it**. The diff
algorithm's hand version is trivial; the db seam is mechanical. Extraction is where
agent-vs-hand actually teaches the principle.

---

## 9. Risks / push back on

1. ~~Join entity over-built~~ **CLOSED (Amendment 1) — accepted.**
2. ~~CSS Modules reflex~~ **CLOSED — Tailwind.** Utility classes keep components self-
   contained and reliably Claude-generated; tradeoff (own the utility vocab) accepted.
3. ~~MCP contrived~~ **CLOSED (Amendment 3) — Filesystem MCP, repo-scoped.**
4. ~~`Active`/`Open` invented~~ **CLOSED (Amendment 4) — explicit manual field, "derived
   by backend in Ex2."**
5. **docx can't preview in-browser** — download-only; docx→PDF preview is scope creep.
   Flag if the demo needs it.
6. **Hebrew RTL rendering** in the profile is deferred polish (`dir="rtl"` per string);
   extraction handles Hebrew, display will look LTR-mixed. Flag if it matters.
7. **Model routing override:** `data-tester` on Sonnet vs your "Haiku for pure-fn tests."
   Push for "Haiku first, escalate on failure" if you want the rule honored literally.
8. **~12 hand-extracted candidates** is real effort on throwaway data; drop to ~6 if slow.
9. **Reflex check — React/Vite/TS:** fits (React ecosystem for Ex3+ chat; clean FastAPI
   seam) but I didn't seriously weigh Svelte/Solid/plain-HTML. Challenge for a lighter stack.

---

## Verification (end-to-end)

- `npm run dev` → every route; PDF link opens, docx downloads.
- `npm run test` (Vitest) green; `/verify-data` → FKs resolve, `sourceCv` paths exist.
- Search/filter candidates; filter positions; compare two near-dup profiles.
- Add → "Pending" badge → reload → resets (proves the honest in-memory gap).
- Fresh clone: `npm i && npm run dev`.

---

---


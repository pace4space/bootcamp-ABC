# Hellio HR — Exercise 1: Candidate Profile Viewer & Diff

UI-only, JSON-backed HR tool. Browse candidates and positions, compare two
candidates side by side, and add/remove candidates to positions in memory.
No database, no auth, no LLM in the running app — those arrive in later
exercises. See `docs/plan-v2.md` for the full design rationale.

**This is Exercise 1 of 8.** Every decision here (data model, async seam,
join entity) is lived with through Exercise 8. The code is written to be
defensible in an interview, not just functional.

---

## Quick start

Requires **Node.js 20.19+ or 22+** (Vite 8 requirement).

```bash
npm install
npm run dev        # → http://localhost:5173
npm run build      # typecheck + production bundle
npm test           # data-layer unit tests (Vitest)
```

---

## Routes & demo walkthrough

| Route | What you see |
|---|---|
| `/candidates` | 11 Active candidates. Search by name; filter by position. |
| `/candidates/:id` | Full profile — skills, experience timeline, education, certifications, languages, CV link, applications. Add/remove positions in memory. |
| `/positions` | 18 Open positions (2 Closed filtered out). Search by title. |
| `/positions/:id` | Full position detail — requirements, description, linked candidates with application statuses. |
| `/compare?a=cv_150&b=cv_202` | Side-by-side diff of two candidates. Shared skills (grey), unique skills (blue/purple), experience columns, education, certifications. |

**Demo URLs to try:**

```
http://localhost:5173/candidates
http://localhost:5173/candidates/cv_004          # Abel McKinney — 3 real applications
http://localhost:5173/positions/job_001           # Senior DevOps Engineer — 2 linked candidates
http://localhost:5173/compare?a=cv_150&b=cv_202  # near-dup Senior Platform Engineers
```

**Add/remove demo:**
1. Go to `/candidates/cv_004`
2. Use the "Add to a position…" dropdown → click **Add**
3. Amber badge appears: "Pending · not saved until Ex2"
4. Navigate to that position's detail — the candidate is listed there too
5. Reload the page — the addition resets (honest about persistence until Ex2)

---

## Project layout

```
src/
  lib/
    types.ts        pure data model — no UI imports, no framework deps
    db.ts           the only data-access seam; async over JSON today,
                    swapped to FastAPI fetch() in Exercise 2 (zero UI change)
    db.test.ts      4 Vitest tests: Active filter, M:N join, sort order, empty case
  data/
    candidates.json   12 candidates (11 Active + 1 Archived)
    positions.json    20 positions (18 Open + 2 Closed)
    applications.json 11 applications (real M:N from source xlsx)
  pages/            CandidatesList, CandidateProfile, Compare, PositionsList, PositionDetail
  components/       AppStatusBadge
  context/          ApplicationsContext — in-memory working copy with add/remove
public/
  cvs/              original CV files — PDF opens in browser, DOCX downloads
  jobs/             original job email files
docs/
  plan-v2.md        full design plan with data model, stack rationale, build order
  architecture.md   Mermaid diagrams: component flow, ER diagram, async seam, Gantt
prompts/            throwaway Ex1 extraction prompts (replaced by real pipeline in Ex3)
scripts/
  verify-data.mjs   validates FKs, source paths, enum values (47 checks)
```

---

## Architecture note

**The `lib/db.ts` seam** is the only place the UI touches data. Today every
function imports from a local JSON file. In Exercise 2, only the function
bodies change to `fetch()` the FastAPI backend — the signatures, return types,
and all UI code remain identical.

**Three entities mirror three future Postgres tables:** `Candidate`,
`Position`, and `Application`. Application is a real M:N join entity (not a
field) because the relationship carries its own `status` attribute and both
screens read it from opposite directions.

---

## Known limitations (Exercise 1)

| Limitation | When it's resolved |
|---|---|
| Add/remove resets on page reload | Exercise 2 (FastAPI + Postgres) |
| DOCX files download instead of previewing in browser | Ex1 scope boundary — browser has no native DOCX renderer |
| Hebrew RTL text in some CVs renders LTR-mixed | Deferred polish — extraction handles Hebrew correctly, display needs `dir="rtl"` per string |
| `status` fields (Active/Open) are manually assigned in JSON | Exercise 2 — derived by the backend based on application history |

---

## Dataset

**12 candidates** — cv_001–cv_008 from the source xlsx (real application links);
cv_100 (Archived, for filter demo); cv_150/cv_202 (near-duplicate Senior Platform
Engineers, for Compare demo); cv_265 (bilingual Hebrew/English career-changer,
for the solve-twice extraction exercise).

**20 positions** — all from the original hiring-manager email files.
job_010 and job_017 are Closed for filter demo.

**11 applications** — real M:N links from the source xlsx, with Waiting/Rejected
statuses where present.

---

## Data integrity

```bash
node scripts/verify-data.mjs   # 47 checks: no dup ids, all FKs resolve, source files exist
```

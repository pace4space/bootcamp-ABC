# Hellio HR

Full-stack HR tool built across 8 progressive exercises. Currently at **Exercise 3 complete / Exercise 4 starting**.

- **Ex1** — React SPA, JSON-backed, candidate viewer + diff
- **Ex2** — FastAPI + Postgres backend, JWT auth, seed pipeline
- **Ex3** — LLM extraction pipeline (Bedrock), ingest endpoint, observability tables
- **Ex4 (next)** — SQL-RAG chat interface over the candidate/position database

Every design decision at Ex1 is carried through to Ex8. Code is written to be defensible in an interview — see `JOURNAL.md` for the reasoning behind non-obvious choices.

---

## Quick start

**Backend + database (Docker):**

```bash
cp .env.example .env          # fill in POSTGRES_PASSWORD, SECRET_KEY, AWS_* credentials
docker compose up --build     # postgres:16 + FastAPI on :8000
docker compose exec api python scripts/seed.py   # first run only
```

**Frontend (Vite dev server):**

```bash
npm install
npm run dev    # → http://localhost:5173
```

**Run API tests:**

```bash
docker compose exec api pytest tests/ -q
```

---

## Demo credentials

| Role | Email | Password | Can do |
|---|---|---|---|
| Admin | `admin@hellio.com` | `admin123` | everything |
| Recruiter | `recruiter@hellio.com` | `recruit123` | upload CV, add/remove applications |
| Viewer | `viewer@hellio.com` | `view123` | read-only |

---

## Routes

| Route | What you see |
|---|---|
| `/candidates` | Candidate list — search by name, filter by position. Checkbox-select two to compare. |
| `/candidates/:id` | Full profile — skills, experience, education, certifications, CV link, linked positions. |
| `/positions` | Open positions. Search by title. |
| `/positions/:id` | Position detail — requirements, description, linked candidates. Admin/recruiter can edit inline. |
| `/compare?a=X&b=Y` | Side-by-side diff — shared/unique skills, experience columns, education, certifications. |
| `/ingest` | Upload a CV (PDF or DOCX). Bedrock extracts → candidate created → link to new profile. |

---

## Demo walkthrough

**Browse + compare:**
1. `/candidates` — see all active candidates
2. Check two candidates → sticky "Compare →" bar appears at bottom → click it
3. Side-by-side skill diff (shared grey, unique blue/purple), experience columns

**Upload + extract:**
1. `/ingest` (admin or recruiter only)
2. Pick a PDF from `CVsJobs/cvs/` (or the generated demo CVs below)
3. Click "Upload & Extract" — Bedrock runs the extraction pipeline
4. Result card shows: status badge (success/partial/failed), run ID, token counts, warnings, "View candidate →" link

**Observe the pipeline:**
```bash
docker compose exec db psql -U hellio hellio -c \
  "SELECT id, status, input_tokens, output_tokens, warnings FROM extraction_runs ORDER BY created_at DESC LIMIT 5;"
```

---

## Demo CV files

Three generated CVs for demo and testing — in `CVsJobs/cvs/`:

| File | Profile |
|---|---|
| `cv_noa_shapiro.pdf` | ML Engineer, 6 yrs, Technion M.Sc., AWS certified |
| `cv_daniel_peretz.pdf` | Full-Stack Engineer, 8 yrs, Lemonade/Fiverr |
| `cv_maya_cohen.pdf` | Platform/DevOps Engineer, CKA certified, Payoneer |

All have LinkedIn URLs, GitHub URLs, and Israeli mobile phones — exercise the heuristic extractor.

---

## Project layout

```
api/
  app/
    pipeline/         Ex3 — 6-stage LLM extraction pipeline
      parsers.py      PDF/DOCX/TXT → RawDocument
      heuristics.py   regex hints (email, phone, LinkedIn, GitHub)
      llm.py          Bedrock converse() + versioned prompts
      validator.py    JSON coercion, hint merge, status assignment
      persister.py    atomic candidate/position DB write
      logger.py       raw_documents + extraction_runs rows
    routers/          auth, candidates, positions, applications, ingest
    models.py         SQLAlchemy ORM (10 tables)
    schemas.py        Pydantic camelCase response schemas
  alembic/            migrations: 0001 initial schema, 0002 pipeline tables
  tests/              101 pytest cases (pipeline unit + endpoint integration)
  uploads/cvs/        ingested CV files served at /api/uploads/cvs/
src/
  lib/
    types.ts          pure data model — no UI imports
    db.ts             async data-access seam (fetch() over FastAPI)
  pages/              CandidatesList, CandidateProfile, Compare, PositionsList, PositionDetail, Ingest
  context/            Auth, Candidates, Positions, Applications
docs/
  ex3/                pipeline design docs (00–08) + pipeline reference
  ex4/                Ex4 plan (SQL-RAG chat, 00–09 + master-plan.md)
CVsJobs/              source CVs and job emails (immutable originals)
```

---

## Architecture

**Data access seam** — `src/lib/db.ts` is the only place the UI touches data. All functions are async. In Ex1 they imported JSON; from Ex2 onward they fetch from FastAPI. Signatures and return types never changed.

**Three normalized entities** — `Candidate`, `Position`, `Application`. Application is a real M:N join entity (not a field) because it carries its own `status` and is read from both directions (candidate → positions, position → candidates).

**Pipeline observability** — every successful ingestion writes to `raw_documents` (parsed text) and `extraction_runs` (full prompt, raw LLM output, token counts, latency, warnings/errors). Validation failures are also logged. Parse and Bedrock failures return HTTP 422 with no DB row.

**Trust hierarchy** — heuristic regex (email, phone, LinkedIn, GitHub) locks in before the LLM call. Heuristic wins silently on overlap. LLM fills semantic fields. Validator coerces types and assigns `success / partial / failed` status.

---

## Database inspection

DBeaver or psql — connect to `localhost:5432`, database `hellio`, user `hellio`, password from `.env`.

Key tables: `candidates`, `candidate_skills`, `candidate_experience`, `positions`, `applications`, `raw_documents`, `extraction_runs`.

---

## Known limitations entering Ex4

| Limitation | Resolved in |
|---|---|
| Bedrock failure after parse produces no DB log | Ex4 pre-work or doc-only fix |
| Auth token not validated on refresh (no `/auth/me`) | Ex4 — `/auth/me` endpoint |
| No pagination on candidate/position lists | Ex6+ |
| CV upload saves bytes but no dedup on identical files | Optional — content-hash check |
| `source_cv_path` null for seeded candidates (shows "Not available") | Acceptable — seeded data pre-dates ingest pipeline |

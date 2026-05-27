# Exercise 2 — Submission

## Artifact 1 — Schema Diagram

See `docs/erd-ex2.png` (editable source: `docs/erd-ex2.drawio`).

11 tables: `users`, `candidates`, `candidate_skills`, `candidate_experience`,
`candidate_education`, `candidate_certifications`, `candidate_languages`,
`positions`, `position_requirements`, `applications`.

---

## Artifact 2 — Git Log

```
* 7a63966 docs: Ex2 complete — criteria verdict, py domain map, Ex3 carry-forward
* 3ec32a9 feat: seam swap — db.ts → fetch(), AuthContext, Login, edit form
* ce401f6 docs: PROGRESS + JOURNAL — seed validated, seam swap next
* c16be3d feat: seed script — candidates.json + positions.json + jobs.xlsx → Postgres
* a5688ab docs: ERD for Ex2 schema + reorganize screenshots under ex1/
* 799e45d feat: FastAPI backend — all routes, JWT auth, 36 tests green
* ce7bb1d chore: clean up planning artifacts; track prompts, arch diagrams, self-check
* de8bdee docs: submission — screenshots of all UI routes + design rationale paragraph
* 354bce4 docs: mark Exercise 1 complete in PROGRESS.md; add Ex2 next-step note
* 541056b docs: README with run instructions, route walkthrough, architecture note
* 96b1620 journal: commit 9 — ApplicationsContext, context-as-working-copy, pendingIds design
* 78fca62 feat: add/remove application (in-memory); populate ApplicationsContext
* 742f8ec chore: Operation SKILLability — learning infrastructure
* e283f59 journal: commit 8 — compare screen, skill set ops, sort stability, query params
* d2fa026 feat: compare screen — side-by-side candidate diff with skill set ops
* 775dee1 journal: commit 7 — positions screens + AppStatusBadge extraction
* ac4f7db feat: positions list + detail screens; extract AppStatusBadge
* 6918c06 journal: commit 6 — candidate profile + architecture diagram
* 4b6c425 feat: candidate profile screen + architecture diagram
* 35f390d journal: commit 5 — candidates list with search and position filter
* 175efd8 feat: candidates list screen with search and position filter
* 9fdf495 chore: extract demo dataset (12 candidates, 20 positions, 11 applications)
* fb57dd0 feat: data layer GREEN — implement filtering and sorting
* b66bcc6 test: data layer RED — test plan + failing assertions
* 3f8b2d6 feat: add pure data model types
* 3fda2ef chore: scaffold Vite + React + TS app shell
```

---

## Artifact 3 — Backend Path: GET /api/candidates/:id

When the frontend calls `GET /api/candidates/cv_004`, the Vite dev server proxy
forwards the request to FastAPI at `localhost:8000`. 

Before the route handler
runs, the `get_current_user` dependency in `auth.py` decodes the Bearer JWT from
the `Authorization` header, verifies the signature against `SECRET_KEY`, and
resolves the caller's identity — returning 401 immediately if the token is missing
or invalid.

 With auth confirmed, the `get_candidate` handler in
`routers/candidates.py` opens an async SQLAlchemy session and executes a single
`SELECT` against the `candidates` table filtered by `id`, augmented with five
`selectinload()` directives — one each for `candidate_skills`,
`candidate_experience`, `candidate_education`, `candidate_certifications`, and
`candidate_languages`. 

SQLAlchemy issues those as five separate
`SELECT … WHERE candidate_id = :id` queries (not JOINs), then assembles all
results into one in-memory `Candidate` ORM object with all relationships
populated. 

The `_to_schema()` function walks that object, converts each sub-list
into the corresponding Pydantic schema using the `alias_generator=to_camel`
config so Python `snake_case` fields become JSON `camelCase`, and returns a
`CandidateSchema`. 

FastAPI serializes it to JSON and responds 200. Six tables
are touched in total: `candidates` plus the five sub-entity tables.

# Hellio HR — API Contract (Exercise 2)

> Ground truth for the FastAPI backend. All response bodies use **camelCase**
> field names, matching `src/lib/types.ts` exactly. The frontend swaps only
> the bodies of `src/lib/db.ts`; signatures and return types are unchanged.

---

## Conventions

| Term | Value |
|---|---|
| Auth header | `Authorization: Bearer <JWT>` |
| Role: recruiter | Any authenticated user |
| Role: admin | User with `role = "admin"` (superset of recruiter) |
| 401 | No token, expired, or invalid token |
| 403 | Valid token but insufficient role |
| 404 | Resource not found |
| 409 | Unique-constraint conflict |
| 422 | Validation error (FastAPI auto-generates body) |

Error body shape: `{ "detail": "<message>" }`

---

## Health

### GET /api/health
- **Auth**: No
- **Response 200**: `{ "status": "ok" }`

---

## Auth

### POST /api/auth/login
- **Auth**: No
- **Body**: `{ "email": "str", "password": "str" }`
- **Response 200** (`LoginResponse`):
  ```json
  {
    "token": "eyJ...",
    "user": { "id": 1, "email": "admin@hellio.com", "role": "admin" }
  }
  ```
- **Errors**: 401 (wrong email/password)

### GET /api/auth/me
- **Auth**: Yes (any role)
- **Response 200** (`UserInfo`):
  ```json
  { "id": 1, "email": "admin@hellio.com", "role": "admin" }
  ```
- **Errors**: 401

---

## Candidates

### GET /api/candidates
Maps to `getCandidates(token)` in `db.ts`.

- **Auth**: Yes (any role)
- **Returns**: `Candidate[]` — Active only, experience sorted by startYear desc
- **Response 200**: array of full `Candidate` objects (same shape as detail endpoint)
- **Errors**: 401

### GET /api/candidates/{id}
Maps to `getCandidate(id, token)` in `db.ts`.

- **Auth**: Yes (any role)
- **Returns**: `Candidate` | 404
- **Response 200** (`Candidate`):
  ```json
  {
    "id": "cv_001",
    "fullName": "Aarav Hayes",
    "headline": "Junior DevOps Engineer",
    "status": "Active",
    "contact": {
      "email": "aarav.hayes@email.com",
      "phone": "060-4281563",
      "city": "Be'er Sheva, Israel",
      "linkedinUrl": "https://linkedin.com/in/aarav-hayes",
      "githubUrl": "https://github.com/aaravhayes"
    },
    "summary": "Motivated Junior DevOps Engineer...",
    "skills": [{ "id": "1", "name": "AWS (EC2, S3, RDS)" }],
    "experience": [
      {
        "id": "1",
        "role": "Junior DevOps Engineer",
        "company": "Company 328",
        "location": "Tel Aviv",
        "startYear": 2023,
        "endYear": null,
        "highlights": ["Maintain and monitor AWS infrastructure"]
      }
    ],
    "education": [
      {
        "id": "1",
        "degree": "DevOps Bootcamp Certificate",
        "institution": "Tech Institute",
        "startYear": 2022,
        "endYear": 2023
      }
    ],
    "certifications": [],
    "languages": [{ "id": "1", "name": "Hebrew", "proficiency": "Native" }],
    "sourceCv": {
      "fileName": "cv_001.pdf",
      "format": "pdf",
      "path": "/cvs/cv_001.pdf"
    }
  }
  ```
- **Notes**:
  - Sub-entity `id` fields are stringified serial ints from Postgres (e.g. `"1"`, `"2"`)
  - `endYear: null` means "currently employed" (Present)
  - `certifications` may be `[]`
- **Errors**: 401, 404

---

## Positions

### GET /api/positions
Maps to `getPositions(token)` in `db.ts`.

- **Auth**: Yes (any role)
- **Returns**: `Position[]` — Open only
- **Response 200**: array of full `Position` objects
- **Errors**: 401

### GET /api/positions/{id}
Maps to `getPosition(id, token)` in `db.ts`.

- **Auth**: Yes (any role)
- **Returns**: `Position` | 404
- **Response 200** (`Position`):
  ```json
  {
    "id": "job_001",
    "title": "Senior DevOps Engineer",
    "status": "Open",
    "hiringManagerEmail": "sarah.chen@company.com",
    "description": "A fast-paced fintech startup...",
    "requirements": {
      "mustHave": ["5+ years hands-on DevOps", "AWS (production)"],
      "niceToHave": ["Prometheus + Grafana"]
    },
    "location": "Tel Aviv (hybrid, 3 days office)",
    "seniority": "Senior",
    "salaryRange": null,
    "sourceDocument": {
      "fileName": "job_001_senior_devops.txt",
      "path": "/jobs/job_001_senior_devops.txt"
    }
  }
  ```
- **Notes**:
  - `requirements` is optional — absent on some positions
  - `salaryRange` may be null (not all positions list salary)
- **Errors**: 401, 404

### PATCH /api/positions/{id}
- **Auth**: Yes — role: admin or recruiter
- **Body** (`PositionPatch`) — all fields optional, send only what changes:
  ```json
  {
    "title": "Lead DevOps Engineer",
    "status": "Closed",
    "description": "Updated description...",
    "location": "Remote",
    "seniority": "Lead",
    "salaryRange": "25,000–30,000 NIS/month",
    "hiringManagerEmail": "new@company.com",
    "requirements": {
      "mustHave": ["8+ years DevOps"],
      "niceToHave": ["Kubernetes"]
    }
  }
  ```
- **Response 200**: full `Position` (updated state)
- **Errors**: 401, 403 (viewer role), 404

---

## Applications

### GET /api/applications
Maps to `getAllApplications(token)`, `getApplicationsByCandidate(id, token)`,
and `getApplicationsByPosition(id, token)` in `db.ts` — unified into one
endpoint with optional query params.

- **Auth**: Yes (any role)
- **Query params** (use at most one):
  - `?candidateId=cv_001` — filter by candidate
  - `?positionId=job_001` — filter by position
- **Response 200**: `Application[]`
  ```json
  [
    { "id": "app-001", "candidateId": "cv_002", "positionId": "job_001", "status": "Waiting" },
    { "id": "app-005", "candidateId": "cv_007", "positionId": "job_002", "status": null }
  ]
  ```
- **Notes**:
  - `status: null` is valid — models an unactioned row (blank Status cell in xlsx)
  - Unknown `candidateId`/`positionId` returns `[]` (not 404)
- **Errors**: 401

### POST /api/applications
- **Auth**: Yes — role: admin or recruiter
- **Body** (`ApplicationCreate`):
  ```json
  { "candidateId": "cv_001", "positionId": "job_005" }
  ```
- **Response 201** (`Application`):
  ```json
  { "id": "app-012", "candidateId": "cv_001", "positionId": "job_005", "status": null }
  ```
- **Errors**: 401, 403 (viewer), 404 (unknown candidateId or positionId), 409 (duplicate pair)

### DELETE /api/applications/{id}
- **Auth**: Yes — role: admin or recruiter
- **Response**: 204 No Content
- **Errors**: 401, 403 (viewer), 404

---

## camelCase field reference

| Python attr | JSON key | Entity |
|---|---|---|
| `full_name` | `fullName` | Candidate |
| `start_year` | `startYear` | ExperienceItem, EducationItem |
| `end_year` | `endYear` | ExperienceItem (nullable), EducationItem |
| `linkedin_url` | `linkedinUrl` | ContactInfo |
| `github_url` | `githubUrl` | ContactInfo |
| `source_cv` | `sourceCv` | Candidate |
| `source_document` | `sourceDocument` | Position |
| `file_name` | `fileName` | SourceDocument, SourceEmail |
| `hiring_manager_email` | `hiringManagerEmail` | Position |
| `must_have` | `mustHave` | Requirements |
| `nice_to_have` | `niceToHave` | Requirements |
| `salary_range` | `salaryRange` | Position |
| `candidate_id` | `candidateId` | Application |
| `position_id` | `positionId` | Application |

---

## Schema dependency graph

```
Skill, ExperienceItem, EducationItem, Certification, Language
  └─► Candidate (GET /candidates, GET /candidates/{id})

ContactInfo, SourceDocument
  └─► Candidate

Requirements, SourceEmail
  └─► Position (GET /positions, GET /positions/{id})

Candidate + Position
  └─► Application (GET /applications, POST /applications)

LoginRequest → LoginResponse (POST /auth/login)
ApplicationCreate → Application (POST /applications)
PositionPatch → Position (PATCH /positions/{id})
```

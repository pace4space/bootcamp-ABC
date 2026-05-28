# Hellio HR Ex2 — Data Flow & Sequence Diagrams

## 1. Authentication Flow

```mermaid
sequenceDiagram
    participant B as Browser
    participant FE as Frontend<br/>AuthContext
    participant BE as Backend<br/>auth.py
    participant DB as PostgreSQL

    B->>BE: POST /api/auth/login<br/>{email, password}
    BE->>DB: SELECT * FROM users WHERE email = ?
    DB-->>BE: user row (with password_hash)
    BE->>BE: bcrypt.verify(password, hash)
    alt Password correct
        BE->>BE: JWT encode {user_id, email, role}
        BE-->>B: 200 {token, user{email, role}}
        B->>FE: store token in context
    else Password wrong
        BE-->>B: 401 Unauthorized
        B->>FE: clear token
    end

    Note over FE: All subsequent requests<br/>include: Authorization: Bearer <token>

    B->>BE: GET /api/candidates
    BE->>BE: depends on get_current_user
    BE->>BE: JWT decode token
    BE->>DB: SELECT * FROM users WHERE id = ?
    DB-->>BE: user object
    alt Token valid & user exists
        BE->>DB: SELECT * FROM candidates WHERE status='Active'
        DB-->>BE: rows
        BE-->>B: 200 [Candidate, ...]
    else Invalid token
        BE-->>B: 401 Unauthorized
    end
```

## 2. Candidate Profile Read (with sub-tables)

```mermaid
sequenceDiagram
    participant UI as React Component
    participant DB as lib/db.ts<br/>(async fetch)
    participant API as candidates.py<br/>GET /candidates/:id
    participant ORM as SQLAlchemy ORM
    participant PG as Postgres

    UI->>DB: getCandidate(id, token)
    DB->>API: fetch /api/candidates/cv_001
    API->>ORM: session.get(Candidate, 'cv_001')
    Note over ORM: Eager load: skills,<br/>experience, education, etc.
    ORM->>PG: SELECT candidates.* FROM candidates<br/>LEFT JOIN candidate_skills ...<br/>LEFT JOIN candidate_experience ...<br/>WHERE candidates.id = 'cv_001'
    PG-->>ORM: rows (with all sub-items)
    ORM->>ORM: model_validate() → ORM objects
    ORM-->>API: Candidate object<br/>(with .skills, .experience lists)
    API->>API: schema.CandidateOut<br/>.model_validate()<br/>snake_case → camelCase
    API-->>DB: 200 {id, fullName, headline,<br/>summary, skills, experience, ...}
    DB-->>UI: Candidate object
    UI->>UI: render profile sections<br/>(skills, experience, education)
```

## 3. Application Creation with Role Check

```mermaid
sequenceDiagram
    participant B as Browser
    participant FE as Frontend<br/>(ApplicationsContext)
    participant API as applications.py<br/>POST /api/applications
    participant AUTH as auth.py<br/>require_role()
    participant ORM as SQLAlchemy ORM
    participant PG as Postgres

    B->>FE: click "Add to position"
    FE->>API: POST /api/applications<br/>{candidateId: 'cv_001',<br/>positionId: 'job_001'}
    API->>AUTH: require_role('admin', 'recruiter')
    alt Token has role: viewer
        AUTH-->>API: 403 Forbidden
        API-->>FE: {error: "Insufficient permissions"}
        FE->>FE: show toast
    else Token has role: recruiter | admin
        AUTH-->>API: user object
        API->>ORM: INSERT applications<br/>VALUES (...)<br/>ON CONFLICT (...) → 409
        ORM->>PG: INSERT
        alt Unique constraint violated
            PG-->>ORM: IntegrityError
            ORM-->>API: 409 Conflict
            API-->>FE: {error: "Already applied"}
            FE->>FE: show error toast
        else Insert succeeds
            PG-->>ORM: new row
            ORM-->>API: Application object
            API-->>FE: 201 {id, candidateId,<br/>positionId, status, createdAt}
            FE->>FE: add to context state
            FE->>FE: optimistically update UI
        end
    end
```

## 4. Position Update (PATCH) with Partial Update

```mermaid
sequenceDiagram
    participant UI as React<br/>PositionDetail
    participant DB as lib/db.ts
    participant API as positions.py<br/>PATCH /positions/:id
    participant AUTH as require_role
    participant ORM as SQLAlchemy
    participant PG as Postgres

    UI->>UI: user edits title field
    UI->>DB: updatePosition(id, {title: "..."}, token)
    DB->>API: PATCH /api/positions/job_001<br/>{title: "New title"}
    API->>AUTH: require_role('admin', 'recruiter')
    alt Permission denied
        AUTH-->>API: 403
        API-->>DB: error
        DB-->>UI: toast error
    else Permission ok
        AUTH-->>API: user
        API->>ORM: session.get(Position, 'job_001')
        ORM->>PG: SELECT * FROM positions WHERE id=?
        PG-->>ORM: row
        ORM->>ORM: Model field update<br/>(title = new value,<br/>other fields unchanged)
        ORM->>PG: UPDATE positions SET title=?<br/>WHERE id='job_001'
        PG-->>ORM: 1 row affected
        ORM->>API: updated Position object
        API->>API: schema.PositionOut.model_validate()
        API-->>DB: 200 {id, title, status,<br/>hirringManagerEmail, ...}
        DB-->>UI: Position object
        UI->>UI: setState(updatedPosition)
        UI->>UI: re-render with new title
    end
```

## 5. List with Filtering & Pagination (future)

```mermaid
sequenceDiagram
    participant UI as CandidatesList
    participant DB as lib/db.ts
    participant API as candidates.py<br/>GET /candidates
    participant PG as Postgres

    UI->>UI: user applies filters<br/>status=Active, position=job_001
    UI->>DB: getCandidates(filters, token)
    DB->>API: fetch /api/candidates<br/>?status=Active&positionId=job_001<br/>&limit=50&cursor=cv_500
    API->>API: parse query params
    API->>PG: SELECT candidates WHERE status=?<br/>AND id IN (<br/>  SELECT candidate_id FROM applications<br/>  WHERE position_id = ?<br/>)<br/>AND id > ?<br/>ORDER BY id<br/>LIMIT 51
    Note over PG: LIMIT 51 to detect<br/>if there's a next page
    PG-->>API: 50 rows
    API->>API: model_validate_list()
    API-->>DB: 200 [Candidate, ...]
    DB-->>UI: candidates array
    UI->>UI: render list
    UI->>UI: compute nextCursor<br/>if length > 50
```

## 6. Data Model Relationships (visual)

```mermaid
graph TB
    subgraph Auth["Auth & Users"]
        Users["🔐 users<br/>id, email, password_hash, role"]
    end

    subgraph Candidates["Candidate Profile"]
        C["👤 candidates<br/>id, fullName, headline, status,<br/>email, phone, city, summary"]
        CSkills["💼 candidate_skills<br/>candidate_id, name, sort_order"]
        CExp["🏢 candidate_experience<br/>candidate_id, role, company,<br/>startYear, endYear, highlights"]
        CEdu["🎓 candidate_education<br/>candidate_id, degree, institution"]
        CCert["📜 candidate_certifications<br/>candidate_id, name, year"]
        CLang["🌍 candidate_languages<br/>candidate_id, name, proficiency"]
        C -->|1:N| CSkills
        C -->|1:N| CExp
        C -->|1:N| CEdu
        C -->|1:N| CCert
        C -->|1:N| CLang
    end

    subgraph Positions["Job Positions"]
        P["📝 positions<br/>id, title, status,<br/>hiringManagerEmail, description"]
        PReq["📋 position_requirements<br/>position_id, type, text, sort_order"]
        P -->|1:N| PReq
    end

    subgraph Applications["Applications (M:N)"]
        App["🤝 applications<br/>id, candidateId, positionId,<br/>status, createdAt<br/><br/>UNIQUE(candidateId, positionId)"]
    end

    C -->|M:N| App
    P -->|M:N| App

    style Users fill:#e8f4f8
    style Candidates fill:#e8f5e9
    style Positions fill:#f1f8e9
    style Applications fill:#fff3e0
```

## 7. Request/Response Contract Example

```mermaid
graph LR
    subgraph Request["HTTP Request"]
        RH["Headers<br/>Authorization: Bearer token<br/>Content-Type: application/json"]
        RB["Body<br/>{<br/>  candidateId: 'cv_001',<br/>  positionId: 'job_001'<br/>}"]
    end

    subgraph Backend["Backend Processing"]
        BE["✓ Auth check (require_role)<br/>✓ FK validation<br/>✓ UNIQUE constraint<br/>✓ Model validation"]
    end

    subgraph Response["HTTP Response"]
        S["201 Created"]
        RES["Body<br/>{<br/>  id: 'app-123',<br/>  candidateId: 'cv_001',<br/>  positionId: 'job_001',<br/>  status: 'Waiting',<br/>  createdAt: '2024-...'<br/>}"]
    end

    Request -->|POST /api/applications| Backend
    Backend -->|Validates| Response
    Response --> S

    style Request fill:#e3f2fd
    style Backend fill:#fff9c4
    style Response fill:#c8e6c9
    style S fill:#4caf50,color:#fff
```

## 8. Deployment Architecture (Ex2 state)

```mermaid
graph TB
    subgraph Client["Client"]
        B["🌐 Browser<br/>Vite SPA<br/>src/"]
    end

    subgraph Dev["Dev Environment"]
        VP["📦 Vite Dev Server<br/>localhost:5173<br/>Proxy /api → :8000"]
        FE["React Components<br/>AuthContext<br/>lib/db.ts"]
    end

    subgraph Server["FastAPI Backend"]
        FA["🚀 FastAPI<br/>localhost:8000"]
        R["Routers<br/>auth, candidates,<br/>positions, applications"]
        AUTH["Auth Middleware<br/>JWT decode<br/>Role checks"]
        ORM["SQLAlchemy ORM<br/>models.py<br/>schemas.py"]
    end

    subgraph Persistence["Persistence"]
        PG["🗄️ PostgreSQL<br/>11 tables<br/>Alembic migrations"]
        FILES["📂 public/cvs/<br/>PDF, DOCX originals"]
    end

    B -->|HTTP + JWT| VP
    VP -->|Routes /api/*| FA
    FA -->|Auth check| AUTH
    AUTH -->|Query| ORM
    ORM -->|SQL| PG
    FA -->|Serve /cvs/*| FILES

    style Client fill:#e1f5ff
    style Dev fill:#f3e5f5
    style Server fill:#fff3e0
    style Persistence fill:#e8f5e9
```

---

## How to read these diagrams

1. **Authentication Flow** — shows JWT generation and validation on every request
2. **Candidate Profile Read** — shows eager-loading of sub-tables (skills, experience, etc.)
3. **Application Creation** — shows role-based access control and unique constraint enforcement
4. **Position Update** — shows partial update logic (PATCH, not overwrite)
5. **List with Filtering** — shows cursor-based pagination (future)
6. **Data Model Relationships** — shows all tables and 1:N, M:N relationships
7. **Request/Response Contract** — shows a real API call with body and status code
8. **Deployment Architecture** — shows how frontend, backend, DB are connected in dev

These diagrams are reference documentation. Copy them into your portfolio or README.

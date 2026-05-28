# Hellio HR Ex2 — Architecture & Request Lifecycle

## System Architecture Diagram

```mermaid
graph TB
    subgraph Frontend["Frontend (Vite + React + TS)"]
        UI["React Components<br/>CandidatesList, Profile, Compare<br/>PositionsList, Detail<br/>Login"]
        AuthCtx["AuthContext<br/>JWT token state"]
        AppCtx["ApplicationsContext<br/>in-memory mutations"]
        DBLayer["lib/db.ts<br/>async getters<br/>getCandidates()<br/>getApplications()"]
    end

    subgraph Seam["Network Seam (Vite Proxy)"]
        Proxy["localhost:5173<br/>→ :8000"]
    end

    subgraph Backend["Backend (FastAPI + SQLAlchemy)"]
        subgraph Routes["Routers"]
            AuthR["auth.py<br/>POST /login<br/>GET /me"]
            CandR["candidates.py<br/>GET /candidates<br/>GET /candidates/:id"]
            PosR["positions.py<br/>GET /positions<br/>GET /positions/:id<br/>PATCH /positions/:id"]
            AppR["applications.py<br/>GET /applications<br/>POST /applications<br/>DELETE /applications/:id"]
        end
        
        subgraph Deps["Dependencies & Auth"]
            GetDB["get_db()<br/>async session"]
            GetUser["get_current_user<br/>JWT decode → user"]
            RoleCheck["require_role<br/>admin/recruiter/viewer"]
        end
        
        subgraph Models["SQLAlchemy Models"]
            UserM["User<br/>id, email, role"]
            CandM["Candidate<br/>id, fullName, status"]
            PosM["Position<br/>id, title, status"]
            AppM["Application<br/>candidateId, positionId, status"]
            SubM["Skills, Experience<br/>Education, Certs, Languages"]
        end
    end

    subgraph Persistence["Persistence"]
        DB["PostgreSQL<br/>11 tables<br/>(candidates, positions,<br/>candidate_skills, etc.)"]
        Files["public/cvs/<br/>PDF + DOCX<br/>originals"]
    end

    UI -->|getCandidates()| DBLayer
    DBLayer -->|fetch GET /api/candidates<br/>+ token| Proxy
    Proxy -->|forward| CandR
    CandR -->|depends| GetDB
    CandR -->|depends| GetUser
    GetUser -->|verify JWT| GetDB
    GetDB -->|SELECT candidates| DB
    CandR -->|model_validate| CandR
    CandR -->|JSON| Proxy
    Proxy -->|response| DBLayer
    DBLayer -->|set candidates state| UI

    AuthCtx -->|token| DBLayer
    AppCtx -->|pendingIds| UI
    DBLayer -->|POST /applications| AppR
    AppR -->|check| RoleCheck
    AppR -->|INSERT| DB
    DB -->|UNIQUE constraint| AppR

    Files -.->|sourceCv link| UI

    style Frontend fill:#e1f5ff
    style Seam fill:#fff3e0
    style Backend fill:#f3e5f5
    style Persistence fill:#e8f5e9

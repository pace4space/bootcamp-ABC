from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# ---------------------------------------------------------------------------
# Shared model config — alias_generator serialises snake_case attrs to
# camelCase JSON, matching src/lib/types.ts exactly.
# from_attributes=True enables model_validate(orm_obj) in routers.
# ---------------------------------------------------------------------------

_CONFIG = ConfigDict(
    alias_generator=to_camel,
    populate_by_name=True,
    from_attributes=True,
)


# ---------------------------------------------------------------------------
# Sub-schemas (defined before parents — no forward refs needed)
# ---------------------------------------------------------------------------

class Skill(BaseModel):
    model_config = _CONFIG

    id: str
    name: str


class ExperienceItem(BaseModel):
    model_config = _CONFIG

    id: str
    role: str
    company: str
    location: Optional[str] = None
    start_year: int
    end_year: Optional[int] = None   # null = "Present" (currently employed)
    highlights: list[str]


class EducationItem(BaseModel):
    model_config = _CONFIG

    id: str
    degree: str
    institution: str
    start_year: int
    end_year: int


class Certification(BaseModel):
    model_config = _CONFIG

    id: str
    name: str
    year: int


class Language(BaseModel):
    model_config = _CONFIG

    id: str
    name: str
    proficiency: str


class SourceDocument(BaseModel):
    """Immutable CV file reference — maps to Candidate.sourceCv in TS."""
    model_config = _CONFIG

    file_name: str
    format: Literal["pdf", "docx"]
    path: str


class SourceEmail(BaseModel):
    """Immutable job-description file reference — maps to Position.sourceDocument in TS."""
    model_config = _CONFIG

    file_name: str
    path: str


class ContactInfo(BaseModel):
    model_config = _CONFIG

    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


class Requirements(BaseModel):
    model_config = _CONFIG

    must_have: list[str]
    nice_to_have: list[str]


# ---------------------------------------------------------------------------
# Top-level entity schemas (match TS types 1-to-1)
# ---------------------------------------------------------------------------

CandidateStatus = Literal["Active", "Archived"]


class Candidate(BaseModel):
    """Full candidate profile — GET /candidates and GET /candidates/{id}."""
    model_config = _CONFIG

    id: str
    full_name: str
    headline: str
    status: CandidateStatus
    contact: ContactInfo
    summary: str
    skills: list[Skill]
    experience: list[ExperienceItem]   # router sorts by start_year desc
    education: list[EducationItem]
    certifications: list[Certification]
    languages: list[Language]
    source_cv: SourceDocument


PositionStatus = Literal["Open", "Closed"]


class Position(BaseModel):
    """Full position detail — GET /positions and GET /positions/{id}."""
    model_config = _CONFIG

    id: str
    title: str
    status: PositionStatus
    hiring_manager_email: str
    description: str
    requirements: Optional[Requirements] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    salary_range: Optional[str] = None
    source_document: SourceEmail


ApplicationStatus = Literal["Waiting", "Rejected", "Screening", "Offer", "Hired"]


class Application(BaseModel):
    """M:N join entity — status is nullable (blank = unactioned row)."""
    model_config = _CONFIG

    id: str
    candidate_id: str
    position_id: str
    status: Optional[ApplicationStatus] = None


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    model_config = _CONFIG

    email: str
    password: str


class UserInfo(BaseModel):
    model_config = _CONFIG

    id: int
    email: str
    role: str


class LoginResponse(BaseModel):
    """Response for POST /auth/login."""
    model_config = _CONFIG

    token: str
    user: UserInfo


# ---------------------------------------------------------------------------
# Request / mutation schemas
# ---------------------------------------------------------------------------

class ApplicationCreate(BaseModel):
    """Body for POST /applications."""
    model_config = _CONFIG

    candidate_id: str
    position_id: str


class PositionPatch(BaseModel):
    """Body for PATCH /positions/{id} — all fields optional (partial update)."""
    model_config = _CONFIG

    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[PositionStatus] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    salary_range: Optional[str] = None
    hiring_manager_email: Optional[str] = None
    requirements: Optional[Requirements] = None


class IngestResponse(BaseModel):
    """Response for POST /api/ingest/cv and POST /api/ingest/position."""
    model_config = _CONFIG

    status: str
    entity_id: Optional[str] = None
    run_id: int
    input_tokens: int
    output_tokens: int
    warnings: list[str] = []
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Chat / SQL-RAG schemas
# ---------------------------------------------------------------------------

class ChatTurn(BaseModel):
    model_config = _CONFIG

    role: str          # 'user' | 'assistant'
    content: str


class ChatRequest(BaseModel):
    model_config = _CONFIG

    question: str
    history: list[ChatTurn] = []
    model: Optional[str] = None      # None → Nova default; not surfaced in UI


class ChatTrace(BaseModel):
    model_config = _CONFIG

    row_count: int
    columns: list[str]
    rows: list[dict] = []            # capped; what was retrieved
    prompt_version: str = "sql-v1"


class ChatResponse(BaseModel):
    model_config = _CONFIG

    answer: str
    sql: str
    status: str                      # ChatStatus value
    model: str
    run_id: int
    trace: ChatTrace
    error: Optional[str] = None
    suggestion: Optional[str] = None

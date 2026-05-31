"""Pipeline-internal type contracts.

Every stage in the pipeline communicates only through these types.
No stage imports from another stage except via this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocumentKind(str, Enum):
    CV = "cv"
    POSITION = "position"


class ParseFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"   # entity created; some fields missing — see warnings
    FAILED = "failed"     # no entity created


@dataclass
class RawDocument:
    """Output of parsers.py. Immutable once created."""
    filename: str
    format: ParseFormat
    kind: DocumentKind
    raw_text: str
    char_count: int


@dataclass
class HeuristicHints:
    """Output of heuristics.py. High-confidence fields extracted by regex.
    These override LLM output for the same field during validation.
    All fields Optional — hints are opportunistic, never blocking.
    """
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    hiring_manager_email: Optional[str] = None  # position docs only


@dataclass
class LLMResponse:
    """Raw output of a single LLM call. Kept verbatim for debugging and replay."""
    model_id: str
    prompt_version: str
    prompt_text: str        # full rendered prompt (system + user) — stored in DB
    raw_json_str: str       # verbatim model reply — stored in DB
    input_tokens: int
    output_tokens: int
    latency_ms: int


# ---------------------------------------------------------------------------
# Payload dataclasses — validated structs passed to persister.py
# ---------------------------------------------------------------------------

@dataclass
class ExperiencePayload:
    role: str
    company: str
    start_year: int
    end_year: Optional[int] = None
    location: Optional[str] = None
    highlights: list[str] = field(default_factory=list)


@dataclass
class EducationPayload:
    degree: str
    institution: str
    start_year: int
    end_year: int


@dataclass
class CertificationPayload:
    name: str
    year: Optional[int] = None


@dataclass
class LanguagePayload:
    name: str
    proficiency: str


@dataclass
class CandidatePayload:
    """Validated candidate fields ready for persistence."""
    full_name: str
    summary: str
    skills: list[str]
    experience: list[ExperiencePayload]
    education: list[EducationPayload]
    certifications: list[CertificationPayload]
    languages: list[LanguagePayload]
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None


@dataclass
class RequirementPayload:
    type: str   # 'must_have' | 'nice_to_have'
    text: str


@dataclass
class PositionPayload:
    """Validated position fields ready for persistence."""
    title: str
    requirements: list[RequirementPayload]
    description: Optional[str] = None
    location: Optional[str] = None
    seniority: Optional[str] = None
    salary_range: Optional[str] = None
    hiring_manager_email: Optional[str] = None


# ---------------------------------------------------------------------------
# ExtractionResult — the pipeline's final return value
# ---------------------------------------------------------------------------

@dataclass
class ExtractionResult:
    status: ExtractionStatus
    document_kind: DocumentKind
    raw_document_id: int         # FK to raw_documents; -1 if parse failed before DB write
    extraction_run_id: int       # FK to extraction_runs; -1 if not logged yet
    entity_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    model_id: str = ""

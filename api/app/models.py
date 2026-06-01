"""SQLAlchemy 2.x ORM models for Hellio HR.

All 11 core tables mirror the exact DDL spec in docs/plan-v2.md.
Ex3 adds two pipeline observability tables: raw_documents, extraction_runs.
Ex5 adds candidate_embeddings / position_embeddings (pgvector, SQLite-portable).

NOTE: ARRAY(Text) columns (highlights, errors, warnings) are Postgres-specific.
Tests against SQLite must patch these columns to JSON() before create_all.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

# vector(512) on Postgres; JSON list-of-floats on SQLite (no native vector type)
EMBEDDING_DIM = 512
EmbeddingType = Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite")


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=True
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'recruiter', 'viewer')", name="users_role_check"),
    )


# ---------------------------------------------------------------------------
# candidates (root entity; child tables reference this via FK)
# ---------------------------------------------------------------------------

class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text, unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_cv_filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_cv_format: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_cv_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('Active', 'Archived')", name="candidates_status_check"),
        CheckConstraint(
            "source_cv_format IN ('pdf', 'docx')",
            name="candidates_source_cv_format_check",
        ),
    )

    # relationships
    skills: Mapped[List[CandidateSkill]] = relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateSkill.sort_order",
    )
    experience: Mapped[List[CandidateExperience]] = relationship(
        "CandidateExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateExperience.sort_order",
    )
    education: Mapped[List[CandidateEducation]] = relationship(
        "CandidateEducation",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateEducation.sort_order",
    )
    certifications: Mapped[List[CandidateCertification]] = relationship(
        "CandidateCertification",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateCertification.sort_order",
    )
    languages: Mapped[List[CandidateLanguage]] = relationship(
        "CandidateLanguage",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="CandidateLanguage.sort_order",
    )
    applications: Mapped[List[Application]] = relationship(
        "Application",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# candidate_skills
# ---------------------------------------------------------------------------

class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="skills")


# ---------------------------------------------------------------------------
# candidate_experience
# NOTE: highlights uses ARRAY(Text) — Postgres-only type.
# ---------------------------------------------------------------------------

class CandidateExperience(Base):
    __tablename__ = "candidate_experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # POSTGRES-SPECIFIC: TEXT[] — not portable to SQLite.
    highlights: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="experience")


# ---------------------------------------------------------------------------
# candidate_education
# ---------------------------------------------------------------------------

class CandidateEducation(Base):
    __tablename__ = "candidate_education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    degree: Mapped[str] = mapped_column(Text, nullable=False)
    institution: Mapped[str] = mapped_column(Text, nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="education")


# ---------------------------------------------------------------------------
# candidate_certifications
# ---------------------------------------------------------------------------

class CandidateCertification(Base):
    __tablename__ = "candidate_certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    candidate: Mapped[Candidate] = relationship(
        "Candidate", back_populates="certifications"
    )


# ---------------------------------------------------------------------------
# candidate_languages
# ---------------------------------------------------------------------------

class CandidateLanguage(Base):
    __tablename__ = "candidate_languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    proficiency: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="languages")


# ---------------------------------------------------------------------------
# positions
# ---------------------------------------------------------------------------

class Position(Base):
    __tablename__ = "positions"

    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    hiring_manager_email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seniority: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document_filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('Open', 'Closed')", name="positions_status_check"),
    )

    requirements: Mapped[List[PositionRequirement]] = relationship(
        "PositionRequirement",
        back_populates="position",
        cascade="all, delete-orphan",
        order_by="PositionRequirement.sort_order",
    )
    applications: Mapped[List[Application]] = relationship(
        "Application",
        back_populates="position",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# position_requirements
# ---------------------------------------------------------------------------

class PositionRequirement(Base):
    __tablename__ = "position_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    position_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    __table_args__ = (
        CheckConstraint(
            "type IN ('must_have', 'nice_to_have')",
            name="position_requirements_type_check",
        ),
    )

    position: Mapped[Position] = relationship("Position", back_populates="requirements")


# ---------------------------------------------------------------------------
# applications  (M:N join with per-link status)
# ---------------------------------------------------------------------------

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("candidates.id", ondelete="CASCADE"),
        nullable=False,
    )
    position_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("positions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('Waiting', 'Rejected', 'Screening', 'Offer', 'Hired')",
            name="applications_status_check",
        ),
        UniqueConstraint("candidate_id", "position_id", name="applications_candidate_position_uniq"),
    )

    candidate: Mapped[Candidate] = relationship("Candidate", back_populates="applications")
    position: Mapped[Position] = relationship("Position", back_populates="applications")


# ---------------------------------------------------------------------------
# raw_documents  (Ex3 pipeline observability — append-only)
# ---------------------------------------------------------------------------

class RawDocument(Base):
    __tablename__ = "raw_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    document_kind: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=True
    )

    __table_args__ = (
        CheckConstraint("format IN ('pdf', 'docx', 'txt')", name="raw_documents_format_check"),
        CheckConstraint(
            "document_kind IN ('cv', 'position')", name="raw_documents_kind_check"
        ),
    )

    extraction_runs: Mapped[List[ExtractionRun]] = relationship(
        "ExtractionRun",
        back_populates="raw_document",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# extraction_runs  (Ex3 pipeline observability — append-only)
# NOTE: errors and warnings use ARRAY(Text) — Postgres-specific.
#       Tests against SQLite must patch these to JSON() before create_all.
# ---------------------------------------------------------------------------

class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_documents.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    raw_llm_output: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # POSTGRES-SPECIFIC: TEXT[] — not portable to SQLite.
    errors: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    warnings: Mapped[List[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    latency_ms: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'partial', 'failed')",
            name="extraction_runs_status_check",
        ),
    )

    raw_document: Mapped[RawDocument] = relationship(
        "RawDocument", back_populates="extraction_runs"
    )


# ---------------------------------------------------------------------------
# query_runs  (Ex4 SQL-RAG observability — append-only)
# Mirrors extraction_runs but SQLite-portable: column list is JSON-in-TEXT,
# no ARRAY columns.
# ---------------------------------------------------------------------------

class QueryRun(Base):
    __tablename__ = "query_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    generated_sql: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(Text, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    columns_json: Mapped[str] = mapped_column(Text, nullable=False, server_default="[]")
    status: Mapped[str] = mapped_column(Text, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), server_default="now()", nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'unsafe', 'sql_error', 'llm_error')",
            name="query_runs_status_check",
        ),
    )


# ---------------------------------------------------------------------------
# candidate_embeddings / position_embeddings  (Ex5 semantic search)
# Dedicated 1:1 tables; FK ON DELETE CASCADE keeps them in sync with core rows.
# EmbeddingType degrades to JSON on SQLite so existing tests need no patch.
# No ANN index at this scale — exact cosine via sequential scan is sub-ms;
# add HNSW (vector_cosine_ops) once N > ~10k rows.
# ---------------------------------------------------------------------------

class CandidateEmbedding(Base):
    __tablename__ = "candidate_embeddings"

    candidate_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("candidates.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list] = mapped_column(EmbeddingType, nullable=False)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    candidate: Mapped[Candidate] = relationship("Candidate")


class PositionEmbedding(Base):
    __tablename__ = "position_embeddings"

    position_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("positions.id", ondelete="CASCADE"), primary_key=True
    )
    embedding: Mapped[list] = mapped_column(EmbeddingType, nullable=False)
    embedding_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    position: Mapped[Position] = relationship("Position")

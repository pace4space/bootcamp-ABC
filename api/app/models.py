"""SQLAlchemy 2.x ORM models for Hellio HR.

All 11 tables mirror the exact DDL spec in docs/plan-v2.md.

NOTE: `candidate_experience.highlights` uses `ARRAY(Text)` from
`sqlalchemy.dialects.postgresql`. This is Postgres-specific; tests that run
against SQLite must either skip the highlights field or patch it out.
"""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
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
    created_at: Mapped[Optional[str]] = mapped_column(
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
    created_at: Mapped[Optional[str]] = mapped_column(
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

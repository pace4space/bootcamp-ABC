"""Pipeline persistence — write validated payload dataclasses into the DB.

Each function creates a savepoint (begin_nested) inside the caller's transaction.
Either all rows for the entity land atomically or none do. The outer transaction
is controlled by the orchestrator; the endpoint commits once.

ID format:
  Candidates → cv_<8 hex chars>  (never collides with seeded cv_001–cv_012)
  Positions  → job_<8 hex chars>
"""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLanguage,
    CandidateSkill,
    Position,
    PositionRequirement,
)

from .types import CandidatePayload, PositionPayload


async def persist_candidate(payload: CandidatePayload, db: AsyncSession) -> str:
    """Insert Candidate + all child rows atomically. Returns candidate_id."""
    candidate_id = f"cv_{uuid4().hex[:8]}"
    async with db.begin_nested():
        candidate = Candidate(
            id=candidate_id,
            full_name=payload.full_name,
            headline=payload.headline,
            status="Active",
            email=payload.email,
            phone=payload.phone,
            city=payload.city,
            linkedin_url=payload.linkedin_url,
            github_url=payload.github_url,
            summary=payload.summary,
        )
        db.add(candidate)
        await db.flush()

        for i, skill in enumerate(payload.skills):
            db.add(CandidateSkill(candidate_id=candidate_id, name=skill, sort_order=i))

        for i, exp in enumerate(payload.experience):
            db.add(CandidateExperience(
                candidate_id=candidate_id,
                role=exp.role,
                company=exp.company,
                location=exp.location,
                start_year=exp.start_year,
                end_year=exp.end_year,
                highlights=exp.highlights,
                sort_order=i,
            ))

        for i, edu in enumerate(payload.education):
            db.add(CandidateEducation(
                candidate_id=candidate_id,
                degree=edu.degree,
                institution=edu.institution,
                start_year=edu.start_year,
                end_year=edu.end_year,
                sort_order=i,
            ))

        for i, cert in enumerate(payload.certifications):
            db.add(CandidateCertification(
                candidate_id=candidate_id,
                name=cert.name,
                year=cert.year,
                sort_order=i,
            ))

        for i, lang in enumerate(payload.languages):
            db.add(CandidateLanguage(
                candidate_id=candidate_id,
                name=lang.name,
                proficiency=lang.proficiency,
                sort_order=i,
            ))

    return candidate_id


async def persist_position(payload: PositionPayload, db: AsyncSession) -> str:
    """Insert Position + requirements atomically. Returns position_id."""
    position_id = f"job_{uuid4().hex[:8]}"
    async with db.begin_nested():
        position = Position(
            id=position_id,
            title=payload.title,
            status="Open",
            description=payload.description,
            location=payload.location,
            seniority=payload.seniority,
            salary_range=payload.salary_range,
            hiring_manager_email=payload.hiring_manager_email,
        )
        db.add(position)
        await db.flush()

        for i, req in enumerate(payload.requirements):
            db.add(PositionRequirement(
                position_id=position_id,
                type=req.type,
                text=req.text,
                sort_order=i,
            ))

    return position_id

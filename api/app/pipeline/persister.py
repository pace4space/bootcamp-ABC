"""Pipeline persistence — write validated payload dataclasses into the DB.

Each function creates a savepoint (begin_nested) inside the caller's transaction.
Either all rows for the entity land atomically or none do. The outer transaction
is controlled by the orchestrator; the endpoint commits once.

ID format:
  Candidates → cv_<8 hex chars>  (never collides with seeded cv_001–cv_012)
  Positions  → job_<8 hex chars>

Upsert semantics:
  persist_candidate matches on email. If a candidate with that email already
  exists, their profile fields and all sub-tables are replaced with the new
  extraction. Application links are preserved — those are HR decisions, not
  CV data. A new extraction_runs row is always written regardless.
"""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
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


async def _replace_sub_tables(candidate_id: str, payload: CandidatePayload, db: AsyncSession) -> None:
    """Delete and re-insert all sub-tables for a candidate."""
    await db.execute(delete(CandidateSkill).where(CandidateSkill.candidate_id == candidate_id))
    await db.execute(delete(CandidateExperience).where(CandidateExperience.candidate_id == candidate_id))
    await db.execute(delete(CandidateEducation).where(CandidateEducation.candidate_id == candidate_id))
    await db.execute(delete(CandidateCertification).where(CandidateCertification.candidate_id == candidate_id))
    await db.execute(delete(CandidateLanguage).where(CandidateLanguage.candidate_id == candidate_id))

    for i, skill in enumerate(payload.skills):
        db.add(CandidateSkill(candidate_id=candidate_id, name=skill, sort_order=i))
    for i, exp in enumerate(payload.experience):
        db.add(CandidateExperience(
            candidate_id=candidate_id, role=exp.role, company=exp.company,
            location=exp.location, start_year=exp.start_year, end_year=exp.end_year,
            highlights=exp.highlights, sort_order=i,
        ))
    for i, edu in enumerate(payload.education):
        db.add(CandidateEducation(
            candidate_id=candidate_id, degree=edu.degree, institution=edu.institution,
            start_year=edu.start_year, end_year=edu.end_year, sort_order=i,
        ))
    for i, cert in enumerate(payload.certifications):
        db.add(CandidateCertification(
            candidate_id=candidate_id, name=cert.name, year=cert.year, sort_order=i,
        ))
    for i, lang in enumerate(payload.languages):
        db.add(CandidateLanguage(
            candidate_id=candidate_id, name=lang.name, proficiency=lang.proficiency, sort_order=i,
        ))


async def persist_candidate(payload: CandidatePayload, db: AsyncSession, filename: str = "") -> str:
    """Upsert candidate by email. Returns candidate_id (existing or new).

    If email already exists: updates profile fields + replaces sub-tables.
    Applications are never touched — those are HR decisions, not CV data.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    cv_format = ext if ext in ("pdf", "docx") else None

    async with db.begin_nested():
        existing_id: str | None = await db.scalar(
            select(Candidate.id).where(Candidate.email == payload.email)
        )

        if existing_id:
            candidate_id = existing_id
            cv_path = f"/api/uploads/cvs/{candidate_id}.{ext}" if cv_format else None
            candidate = await db.get(Candidate, candidate_id)
            candidate.full_name = payload.full_name
            candidate.headline = payload.headline
            candidate.phone = payload.phone
            candidate.city = payload.city
            candidate.linkedin_url = payload.linkedin_url
            candidate.github_url = payload.github_url
            candidate.summary = payload.summary
            candidate.source_cv_filename = filename or None
            candidate.source_cv_format = cv_format
            candidate.source_cv_path = cv_path
            await db.flush()
            await _replace_sub_tables(candidate_id, payload, db)
        else:
            candidate_id = f"cv_{uuid4().hex[:8]}"
            cv_path = f"/api/uploads/cvs/{candidate_id}.{ext}" if cv_format else None
            db.add(Candidate(
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
                source_cv_filename=filename or None,
                source_cv_format=cv_format,
                source_cv_path=cv_path,
            ))
            await db.flush()
            await _replace_sub_tables(candidate_id, payload, db)

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

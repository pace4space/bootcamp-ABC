from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    Candidate,
    CandidateCertification,
    CandidateEducation,
    CandidateExperience,
    CandidateLanguage,
    CandidateSkill,
    User,
)
from app.schemas import (
    Candidate as CandidateSchema,
    Certification,
    ContactInfo,
    EducationItem,
    ExperienceItem,
    Language,
    Skill,
    SourceDocument,
)

router = APIRouter(tags=["candidates"])

_EAGER = [
    selectinload(Candidate.skills),
    selectinload(Candidate.experience),
    selectinload(Candidate.education),
    selectinload(Candidate.certifications),
    selectinload(Candidate.languages),
]


def _to_schema(c: Candidate) -> CandidateSchema:
    return CandidateSchema(
        id=c.id,
        full_name=c.full_name,
        headline=c.headline or "",
        status=c.status,
        contact=ContactInfo(
            email=c.email or "",
            phone=c.phone,
            city=c.city,
            linkedin_url=c.linkedin_url,
            github_url=c.github_url,
        ),
        summary=c.summary or "",
        skills=[Skill(id=str(s.id), name=s.name) for s in c.skills],
        experience=sorted(
            [
                ExperienceItem(
                    id=str(e.id),
                    role=e.role,
                    company=e.company,
                    location=e.location,
                    start_year=e.start_year,
                    end_year=e.end_year,
                    highlights=e.highlights or [],
                )
                for e in c.experience
            ],
            key=lambda x: x.start_year,
            reverse=True,
        ),
        education=[
            EducationItem(
                id=str(ed.id),
                degree=ed.degree,
                institution=ed.institution,
                start_year=ed.start_year,
                end_year=ed.end_year,
            )
            for ed in c.education
        ],
        certifications=[
            Certification(id=str(cert.id), name=cert.name, year=cert.year or 0)
            for cert in c.certifications
        ],
        languages=[
            Language(id=str(lang.id), name=lang.name, proficiency=lang.proficiency)
            for lang in c.languages
        ],
        source_cv=SourceDocument(
            file_name=c.source_cv_filename or "",
            format=c.source_cv_format or "pdf",
            path=c.source_cv_path or "",
        ),
    )


@router.get("/candidates", response_model=list[CandidateSchema])
async def list_candidates(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CandidateSchema]:
    result = await db.execute(
        select(Candidate)
        .where(Candidate.status == "Active")
        .options(*_EAGER)
        .order_by(Candidate.full_name)
    )
    return [_to_schema(c) for c in result.scalars().all()]


@router.get("/candidates/{candidate_id}", response_model=CandidateSchema)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> CandidateSchema:
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id).options(*_EAGER)
    )
    candidate = result.scalar_one_or_none()
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
    return _to_schema(candidate)

"""DB-backed unit tests for pipeline/persister.py.

Uses the seeded_db fixture (SQLite in-memory).
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models import Candidate, CandidateSkill, CandidateExperience, Position
from app.pipeline.persister import persist_candidate, persist_position
from app.pipeline.types import (
    CandidatePayload,
    CertificationPayload,
    ExperiencePayload,
    LanguagePayload,
    PositionPayload,
    RequirementPayload,
)


def _minimal_candidate(**overrides) -> CandidatePayload:
    defaults = dict(
        full_name="Test Candidate",
        summary="A summary.",
        skills=[],
        experience=[],
        education=[],
        certifications=[],
        languages=[],
    )
    return CandidatePayload(**{**defaults, **overrides})


def _minimal_position(**overrides) -> PositionPayload:
    defaults = dict(
        title="Software Engineer",
        requirements=[],
    )
    return PositionPayload(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# persist_candidate
# ---------------------------------------------------------------------------

async def test_persist_candidate_id_format(seeded_db):
    async with seeded_db() as db:
        cid = await persist_candidate(_minimal_candidate(), db)
        await db.commit()

    # "cv_" + 8 hex chars = 11 chars total
    assert cid.startswith("cv_")
    assert len(cid) == 11


async def test_persist_candidate_all_children_written(seeded_db):
    payload = _minimal_candidate(
        skills=["Python", "Docker", "Kubernetes"],
        experience=[
            ExperiencePayload(role="SRE", company="Acme", start_year=2021),
            ExperiencePayload(role="DevOps", company="Corp", start_year=2019, end_year=2020),
        ],
    )
    async with seeded_db() as db:
        cid = await persist_candidate(payload, db)
        await db.commit()

    async with seeded_db() as db:
        result = await db.execute(
            select(Candidate)
            .where(Candidate.id == cid)
            .options(
                selectinload(Candidate.skills),
                selectinload(Candidate.experience),
            )
        )
        candidate = result.scalar_one()
        assert len(candidate.skills) == 3
        assert len(candidate.experience) == 2
        assert {s.name for s in candidate.skills} == {"Python", "Docker", "Kubernetes"}


async def test_persist_candidate_with_no_children(seeded_db):
    async with seeded_db() as db:
        cid = await persist_candidate(_minimal_candidate(), db)
        await db.commit()

    async with seeded_db() as db:
        result = await db.execute(select(Candidate).where(Candidate.id == cid))
        candidate = result.scalar_one()
        assert candidate.full_name == "Test Candidate"
        assert candidate.status == "Active"


async def test_persist_candidate_unique_ids(seeded_db):
    """Two different people (different emails) must get distinct generated ids."""
    async with seeded_db() as db:
        id1 = await persist_candidate(_minimal_candidate(email="a@test.com"), db)
        id2 = await persist_candidate(_minimal_candidate(email="b@test.com"), db)
        await db.commit()

    assert id1 != id2


# ---------------------------------------------------------------------------
# persist_position
# ---------------------------------------------------------------------------

async def test_persist_position_id_format(seeded_db):
    async with seeded_db() as db:
        pid = await persist_position(_minimal_position(), db)
        await db.commit()

    assert pid.startswith("job_")
    assert len(pid) == 12  # "job_" + 8 hex


async def test_persist_position_with_requirements(seeded_db):
    payload = _minimal_position(
        requirements=[
            RequirementPayload(type="must_have", text="Python"),
            RequirementPayload(type="nice_to_have", text="Kubernetes"),
        ]
    )
    async with seeded_db() as db:
        pid = await persist_position(payload, db)
        await db.commit()

    async with seeded_db() as db:
        result = await db.execute(
            select(Position)
            .where(Position.id == pid)
            .options(selectinload(Position.requirements))
        )
        pos = result.scalar_one()
        assert pos.title == "Software Engineer"
        assert pos.status == "Open"
        assert len(pos.requirements) == 2

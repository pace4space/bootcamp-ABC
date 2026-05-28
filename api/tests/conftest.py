"""Test fixtures for Hellio HR API.

SQLite-specific patches applied before create_all:
- CandidateExperience.highlights: ARRAY(Text) → JSON (SQLite has no native array type)
- Own engine with no pool_size/max_overflow (invalid kwargs for SQLite)
- User.created_at / Application.created_at server_default='now()' is Postgres syntax;
  supply Python datetime values at insert time so SQLite never sees the literal string.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import JSON
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.auth import create_access_token, hash_password
from app.db import get_db
from app.main import app
from app.models import (
    Base,
    Application,
    Candidate,
    CandidateExperience,
    CandidateLanguage,
    CandidateSkill,
    ExtractionRun,
    Position,
    PositionRequirement,
    RawDocument,
    User,
)

_NOW = datetime.now(timezone.utc)


@pytest.fixture
async def engine():
    # Patch all Postgres ARRAY(Text) columns to JSON() for SQLite compatibility
    CandidateExperience.__table__.c.highlights.type = JSON()
    ExtractionRun.__table__.c.errors.type = JSON()
    ExtractionRun.__table__.c.warnings.type = JSON()

    test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )() as session:
        # Users — supply created_at explicitly: server_default='now()' is Postgres-only
        admin = User(email="admin@hellio.com", password_hash=hash_password("admin123"), role="admin", created_at=_NOW)
        recruiter = User(email="recruiter@hellio.com", password_hash=hash_password("recruiter123"), role="recruiter", created_at=_NOW)
        viewer = User(email="viewer@hellio.com", password_hash=hash_password("viewer123"), role="viewer", created_at=_NOW)
        session.add_all([admin, recruiter, viewer])
        await session.flush()  # assigns autoincrement ids

        # Candidates
        c01 = Candidate(
            id="cv_t01", full_name="Alice Tester", status="Active", email="alice@test.com",
            headline="Senior DevOps Engineer", summary="Experienced DevOps.",
            source_cv_filename="alice.pdf", source_cv_format="pdf", source_cv_path="/cvs/alice.pdf",
        )
        c02 = Candidate(
            id="cv_t02", full_name="Bob Tester", status="Active", email="bob@test.com",
            headline="DevOps Engineer", summary="Solid DevOps.",
            source_cv_filename="bob.pdf", source_cv_format="pdf", source_cv_path="/cvs/bob.pdf",
        )
        c99 = Candidate(
            id="cv_t99", full_name="Carol Archived", status="Archived", email="carol@test.com",
            headline="Former DevOps", summary="Archived candidate.",
            source_cv_filename="carol.pdf", source_cv_format="pdf", source_cv_path="/cvs/carol.pdf",
        )
        session.add_all([c01, c02, c99])
        await session.flush()

        # CandidateExperience — sort_order determines DB ordering; tests verify startYear sort
        session.add_all([
            CandidateExperience(candidate_id="cv_t01", role="Senior DevOps", company="ACME",
                                start_year=2022, end_year=None, highlights=[], sort_order=0),
            CandidateExperience(candidate_id="cv_t01", role="DevOps Engineer", company="Corp",
                                start_year=2020, end_year=2021, highlights=[], sort_order=1),
            CandidateExperience(candidate_id="cv_t02", role="Junior DevOps", company="Startup",
                                start_year=2021, end_year=None, highlights=[], sort_order=0),
            CandidateExperience(candidate_id="cv_t99", role="DevOps", company="OldCo",
                                start_year=2019, end_year=None, highlights=[], sort_order=0),
        ])

        # CandidateSkill for cv_t01 — ensures skills list is non-empty in detail test
        session.add(CandidateSkill(candidate_id="cv_t01", name="Docker", sort_order=0))

        # CandidateLanguage for cv_t01 — ensures languages list is non-empty in detail test
        session.add(CandidateLanguage(candidate_id="cv_t01", name="English", proficiency="Native", sort_order=0))

        # Positions
        p01 = Position(
            id="pos_t01", title="Test Position Open A", status="Open",
            hiring_manager_email="manager@test.com", description="Open position A.",
            source_document_filename="jobA.pdf", source_document_path="/jobs/jobA.pdf",
        )
        p02 = Position(
            id="pos_t02", title="Test Position Open B", status="Open",
            hiring_manager_email="manager@test.com", description="Open position B.",
            source_document_filename="jobB.pdf", source_document_path="/jobs/jobB.pdf",
        )
        p03 = Position(
            id="pos_t03", title="Test Position Closed", status="Closed",
            hiring_manager_email="manager@test.com", description="Closed position.",
            source_document_filename="jobC.pdf", source_document_path="/jobs/jobC.pdf",
        )
        session.add_all([p01, p02, p03])
        await session.flush()

        # PositionRequirements — pos_t02 intentionally has none
        session.add_all([
            PositionRequirement(position_id="pos_t01", type="must_have", text="Docker", sort_order=0),
            PositionRequirement(position_id="pos_t01", type="nice_to_have", text="Kubernetes", sort_order=0),
            PositionRequirement(position_id="pos_t03", type="must_have", text="Python", sort_order=0),
        ])

        # Applications — supply created_at explicitly for same reason as Users
        session.add_all([
            Application(id="app_t01", candidate_id="cv_t01", position_id="pos_t01", status="Waiting", created_at=_NOW),
            Application(id="app_t02", candidate_id="cv_t02", position_id="pos_t01", status=None, created_at=_NOW),
            Application(id="app_t03", candidate_id="cv_t01", position_id="pos_t02", status="Rejected", created_at=_NOW),
        ])

        await session.commit()

    yield test_engine

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def seeded_db(engine):
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    yield factory


@pytest.fixture
async def client(seeded_db):
    async def override_get_db():
        async with seeded_db() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(seeded_db):
    async with seeded_db() as session:
        from sqlalchemy import select
        from app.models import User
        result = await session.execute(select(User).where(User.email == "admin@hellio.com"))
        user = result.scalar_one()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def recruiter_headers(seeded_db):
    async with seeded_db() as session:
        from sqlalchemy import select
        from app.models import User
        result = await session.execute(select(User).where(User.email == "recruiter@hellio.com"))
        user = result.scalar_one()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def viewer_headers(seeded_db):
    async with seeded_db() as session:
        from sqlalchemy import select
        from app.models import User
        result = await session.execute(select(User).where(User.email == "viewer@hellio.com"))
        user = result.scalar_one()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}

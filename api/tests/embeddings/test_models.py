"""Segment 01 tests — embedding table round-trips + cascade delete.

Proves:
1. CandidateEmbedding and PositionEmbedding persist and round-trip a 512-float vector.
2. Cascade delete removes the embedding row when the parent is deleted.
3. The with_variant(JSON, "sqlite") keeps create_all working (implicit: fixtures succeed).
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import (
    Candidate,
    CandidateEmbedding,
    Position,
    PositionEmbedding,
)

_NOW = datetime.now(timezone.utc)
_VEC = [float(i) / 512 for i in range(512)]
_SHA = "a" * 64


@pytest.fixture
async def db(engine):
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


async def test_candidate_embedding_roundtrip(db: AsyncSession):
    row = CandidateEmbedding(
        candidate_id="cv_t01",
        embedding=_VEC,
        embedding_text="test embedding text",
        embedding_model="mock-titan",
        text_sha256=_SHA,
        updated_at=_NOW,
    )
    db.add(row)
    await db.flush()
    await db.commit()

    result = await db.execute(
        select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == "cv_t01")
    )
    fetched = result.scalar_one()
    assert fetched.embedding == _VEC
    assert fetched.text_sha256 == _SHA
    assert fetched.embedding_text == "test embedding text"


async def test_position_embedding_roundtrip(db: AsyncSession):
    row = PositionEmbedding(
        position_id="pos_t01",
        embedding=_VEC,
        embedding_text="test position text",
        embedding_model="mock-titan",
        text_sha256=_SHA,
        updated_at=_NOW,
    )
    db.add(row)
    await db.flush()
    await db.commit()

    result = await db.execute(
        select(PositionEmbedding).where(PositionEmbedding.position_id == "pos_t01")
    )
    fetched = result.scalar_one()
    assert fetched.embedding == _VEC
    assert fetched.text_sha256 == _SHA
    assert fetched.embedding_text == "test position text"


async def test_cascade_delete(db: AsyncSession):
    row = CandidateEmbedding(
        candidate_id="cv_t02",
        embedding=_VEC,
        embedding_text="to be deleted",
        embedding_model="mock-titan",
        text_sha256=_SHA,
        updated_at=_NOW,
    )
    db.add(row)
    await db.flush()

    candidate = await db.get(Candidate, "cv_t02")
    await db.delete(candidate)
    await db.commit()

    result = await db.execute(
        select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == "cv_t02")
    )
    assert result.scalar_one_or_none() is None

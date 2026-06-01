"""Segment 04 tests — embedding service (upsert + backfill)."""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.embeddings.service import backfill_all, upsert_candidate_embedding
from app.embeddings.text_builder import build_candidate_text
from app.models import CandidateEmbedding, PositionEmbedding
from tests.embeddings.conftest import MockEmbeddingClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def db(seeded_db):
    async with seeded_db() as session:
        yield session


@pytest.fixture
def mock_client():
    return MockEmbeddingClient()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_backfill_embeds_all(db: AsyncSession, mock_client):
    with patch("app.embeddings.service.BedrockClient", return_value=mock_client):
        report = await backfill_all(db, mock_client)
        await db.commit()

    # seeded DB has 3 candidates + 3 positions
    assert report.candidates_embedded == 3
    assert report.positions_embedded == 3
    assert report.skipped == 0
    assert report.total_tokens > 0

    # rows exist in DB
    cand_rows = (await db.execute(select(CandidateEmbedding))).scalars().all()
    pos_rows = (await db.execute(select(PositionEmbedding))).scalars().all()
    assert len(cand_rows) == 3
    assert len(pos_rows) == 3


async def test_backfill_idempotent(db: AsyncSession, mock_client):
    with patch("app.embeddings.service.BedrockClient", return_value=mock_client):
        await backfill_all(db, mock_client)
        await db.commit()
        report2 = await backfill_all(db, mock_client)
        await db.commit()

    assert report2.candidates_embedded == 0
    assert report2.positions_embedded == 0
    assert report2.skipped == 6  # all 3 candidates + 3 positions skipped


async def test_reembed_on_text_change(db: AsyncSession, mock_client):
    from sqlalchemy.orm import selectinload
    from app.models import Candidate

    # backfill first
    await backfill_all(db, mock_client)
    await db.commit()

    old_sha = (await db.get(CandidateEmbedding, "cv_t01")).text_sha256

    # reload with eager-loaded children so build_candidate_text doesn't lazy-load
    result = await db.execute(
        select(Candidate).where(Candidate.id == "cv_t01")
        .options(
            selectinload(Candidate.skills),
            selectinload(Candidate.experience),
            selectinload(Candidate.education),
            selectinload(Candidate.certifications),
            selectinload(Candidate.languages),
        )
    )
    c = result.scalar_one()
    c.summary = "CHANGED: kubernetes platform engineer with 10 years Terraform."
    await db.flush()

    re_embedded = await upsert_candidate_embedding(c, db, mock_client)
    await db.commit()

    assert re_embedded is True
    new_row = await db.get(CandidateEmbedding, "cv_t01")
    assert new_row.text_sha256 != old_sha


async def test_embedding_text_stored_matches_builder(db: AsyncSession, mock_client):
    await backfill_all(db, mock_client)
    await db.commit()

    from sqlalchemy.orm import selectinload
    from app.models import Candidate
    result = await db.execute(
        select(Candidate).where(Candidate.id == "cv_t01")
        .options(
            selectinload(Candidate.skills),
            selectinload(Candidate.experience),
            selectinload(Candidate.education),
            selectinload(Candidate.certifications),
            selectinload(Candidate.languages),
        )
    )
    c = result.scalar_one()
    expected_text = build_candidate_text(c)
    row = await db.get(CandidateEmbedding, "cv_t01")
    assert row.embedding_text == expected_text


async def test_skip_returns_false(db: AsyncSession, mock_client):
    from sqlalchemy.orm import selectinload
    from app.models import Candidate
    result = await db.execute(
        select(Candidate).where(Candidate.id == "cv_t01")
        .options(
            selectinload(Candidate.skills),
            selectinload(Candidate.experience),
            selectinload(Candidate.education),
            selectinload(Candidate.certifications),
            selectinload(Candidate.languages),
        )
    )
    c = result.scalar_one()

    first = await upsert_candidate_embedding(c, db, mock_client)
    await db.commit()
    assert first is True

    # second call with same text — must skip without an embed call
    call_count_before = 0  # mock has no call counter; we track via embed_with_usage
    original_embed = mock_client.embed_with_usage
    calls = []
    def counting_embed(text):
        calls.append(text)
        return original_embed(text)
    mock_client.embed_with_usage = counting_embed

    second = await upsert_candidate_embedding(c, db, mock_client)
    await db.commit()
    assert second is False
    assert len(calls) == 0   # no Bedrock call on skip

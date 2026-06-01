"""Segment 05 tests — vector retrieval search (cosine top-N + exclusion)."""
from __future__ import annotations

import math
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.search import (
    SIMILARITY_THRESHOLD,
    cosine,
    rank_top_n,
    search_candidates_for_position,
    search_positions_for_candidate,
)
from app.embeddings.service import backfill_all
from tests.embeddings.conftest import MockEmbeddingClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    return MockEmbeddingClient()


@pytest.fixture
async def seeded_embeddings(seeded_db, mock_client):
    """Backfill all embeddings with mock vectors so search functions have data."""
    async with seeded_db() as db:
        await backfill_all(db, mock_client)
        await db.commit()
    async with seeded_db() as db:
        yield db


# ---------------------------------------------------------------------------
# Pure-logic tests (no DB)
# ---------------------------------------------------------------------------

def test_rank_top_n_pure():
    scored = [("a", 0.9), ("b", 0.7), ("c", 0.8), ("d", 0.3)]
    result = rank_top_n(scored, exclude={"b"}, threshold=0.5, n=2)
    ids = [r[0] for r in result]
    scores = [r[1] for r in result]
    assert "b" not in ids              # excluded
    assert "d" not in ids              # below threshold
    assert ids == ["a", "c"]           # sorted desc
    assert scores == [0.9, 0.8]


def test_rank_top_n_cap():
    scored = [(str(i), float(i) / 10) for i in range(10, 0, -1)]
    result = rank_top_n(scored, exclude=set(), threshold=0.0, n=3)
    assert len(result) == 3


def test_cosine_basic():
    v = [1.0, 0.0, 0.0]
    assert abs(cosine(v, v) - 1.0) < 1e-9        # same vector → 1.0

    v2 = [0.0, 1.0, 0.0]
    assert abs(cosine(v, v2)) < 1e-9              # orthogonal → ~0

    v3 = [-1.0, 0.0, 0.0]
    assert abs(cosine(v, v3) + 1.0) < 1e-9       # opposite → -1.0


# ---------------------------------------------------------------------------
# Service-level tests (with seeded SQLite DB + mock embeddings)
# ---------------------------------------------------------------------------

async def test_candidates_for_position_excludes_linked(seeded_embeddings: AsyncSession):
    # cv_t01 and cv_t02 are linked to pos_t01 via applications
    results = await search_candidates_for_position(
        "pos_t01", seeded_embeddings, threshold=0.0
    )
    linked = {"cv_t01", "cv_t02"}
    for sc in results:
        assert sc.candidate_id not in linked


async def test_threshold_suppresses(seeded_embeddings: AsyncSession):
    results = await search_candidates_for_position(
        "pos_t01", seeded_embeddings, threshold=0.9999
    )
    # mock vectors will rarely score this high unless texts are identical
    assert results == []


async def test_top_n_cap(seeded_embeddings: AsyncSession):
    results = await search_candidates_for_position(
        "pos_t02", seeded_embeddings, top_n=2, threshold=0.0
    )
    assert len(results) <= 2
    if len(results) > 1:
        assert results[0].score >= results[1].score   # sorted desc


async def test_positions_for_candidate_symmetry(seeded_embeddings: AsyncSession):
    # cv_t01 applied to pos_t01 and pos_t02 → both should be excluded
    results = await search_positions_for_candidate(
        "cv_t01", seeded_embeddings, threshold=0.0
    )
    applied = {"pos_t01", "pos_t02"}
    for sp in results:
        assert sp.position_id not in applied


async def test_no_stored_vector_returns_empty(seeded_embeddings: AsyncSession):
    # Use a non-existent id that has no embedding row
    results = await search_candidates_for_position(
        "pos_nonexistent", seeded_embeddings, threshold=0.0
    )
    assert results == []

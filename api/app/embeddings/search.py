"""Vector retrieval: cosine top-N + relational exclusion + threshold.

Design principle: reuse the entity's STORED vector as query (no live embed).
- Fast, reproducible: same inputs → same ranking every time.
- Separates pure ranking logic (cosine, rank_top_n) from dialect-specific
  distance computation so both halves are independently testable.
- The NOT IN (applications ...) exclusion is the seam where future relational
  filters (seniority, department, availability) bolt on — one query.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import engine as _async_engine
from app.models import Application, CandidateEmbedding, PositionEmbedding


def _to_pgvector_str(vec: list[float]) -> str:
    """Format a vector as pgvector literal: '[f1,f2,...,fn]' (no spaces, no newlines).

    str(numpy_array) produces numpy format with spaces/newlines which pgvector rejects.
    """
    return "[" + ",".join(str(float(v)) for v in vec) + "]"

SIMILARITY_THRESHOLD = float(os.getenv("EMBED_SIM_THRESHOLD", "0.5"))


@dataclass
class ScoredCandidate:
    candidate_id: str
    score: float


@dataclass
class ScoredPosition:
    position_id: str
    score: float


# ---------------------------------------------------------------------------
# Pure logic — no DB; fully unit-testable on any platform
# ---------------------------------------------------------------------------

def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity.  Inputs may already be unit-norm."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    denom = norm_a * norm_b
    return dot / denom if denom else 0.0


def rank_top_n(
    scored: list[tuple[str, float]],
    exclude: set[str],
    threshold: float,
    n: int,
) -> list[tuple[str, float]]:
    """Drop excluded ids, drop score < threshold, sort desc, cap at n."""
    filtered = [
        (id_, score)
        for id_, score in scored
        if id_ not in exclude and score >= threshold
    ]
    filtered.sort(key=lambda x: x[1], reverse=True)
    return filtered[:n]


# ---------------------------------------------------------------------------
# Service functions — dialect-branched distance, shared ranking
# ---------------------------------------------------------------------------

async def search_candidates_for_position(
    position_id: str,
    db: AsyncSession,
    *,
    top_n: int = 3,
    threshold: float | None = None,
) -> list[ScoredCandidate]:
    """Return top-N candidates most similar to a position, excluding linked ones.

    threshold=None uses the module-level SIMILARITY_THRESHOLD (patchable in tests).
    """
    """Return top-N candidates most similar to a position, excluding linked ones."""
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD

    pos_row = await db.get(PositionEmbedding, position_id)
    if pos_row is None:
        return []

    qvec = pos_row.embedding

    # linked candidates to exclude (relational filter seam)
    app_result = await db.execute(
        select(Application.candidate_id).where(Application.position_id == position_id)
    )
    exclude = {row[0] for row in app_result}

    bind = db.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        rows_result = await db.execute(select(CandidateEmbedding))
        rows = rows_result.scalars().all()
        scored: list[tuple[str, float]] = [
            (row.candidate_id, cosine(qvec, row.embedding)) for row in rows
        ]
    else:
        # Postgres: single SQL query with pgvector <=> operator
        sql = text("""
            SELECT candidate_id, 1 - (embedding <=> CAST(:qvec AS vector)) AS score
            FROM candidate_embeddings
            WHERE candidate_id NOT IN (
                SELECT candidate_id FROM applications WHERE position_id = :pid
            )
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """)
        import json
        async with _async_engine.connect() as conn:
            result = await conn.execute(
                sql,
                {"qvec": _to_pgvector_str(qvec), "pid": position_id, "k": top_n},
            )
            scored = [(row.candidate_id, float(row.score)) for row in result]

    ranked = rank_top_n(scored, exclude, threshold, top_n)
    return [ScoredCandidate(candidate_id=id_, score=score) for id_, score in ranked]


async def search_positions_for_candidate(
    candidate_id: str,
    db: AsyncSession,
    *,
    top_n: int = 3,
    threshold: float | None = None,
) -> list[ScoredPosition]:
    """Return top-N positions most similar to a candidate, excluding applied ones.

    threshold=None uses the module-level SIMILARITY_THRESHOLD (patchable in tests).
    """
    if threshold is None:
        threshold = SIMILARITY_THRESHOLD

    cand_row = await db.get(CandidateEmbedding, candidate_id)
    if cand_row is None:
        return []

    qvec = cand_row.embedding

    # already-applied positions to exclude
    app_result = await db.execute(
        select(Application.position_id).where(Application.candidate_id == candidate_id)
    )
    exclude = {row[0] for row in app_result}

    bind = db.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        rows_result = await db.execute(select(PositionEmbedding))
        rows = rows_result.scalars().all()
        scored: list[tuple[str, float]] = [
            (row.position_id, cosine(qvec, row.embedding)) for row in rows
        ]
    else:
        sql = text("""
            SELECT position_id, 1 - (embedding <=> CAST(:qvec AS vector)) AS score
            FROM position_embeddings
            WHERE position_id NOT IN (
                SELECT position_id FROM applications WHERE candidate_id = :cid
            )
            ORDER BY embedding <=> CAST(:qvec AS vector)
            LIMIT :k
        """)
        async with _async_engine.connect() as conn:
            result = await conn.execute(
                sql,
                {"qvec": _to_pgvector_str(qvec), "cid": candidate_id, "k": top_n},
            )
            scored = [(row.position_id, float(row.score)) for row in result]

    ranked = rank_top_n(scored, exclude, threshold, top_n)
    return [ScoredPosition(position_id=id_, score=score) for id_, score in ranked]

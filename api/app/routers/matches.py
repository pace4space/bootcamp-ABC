"""Match endpoints for Ex5 semantic search.

GET /api/positions/{position_id}/candidate-matches  → list[CandidateMatch]
GET /api/candidates/{candidate_id}/position-matches → list[PositionMatch]

Read-only — any authenticated user (incl. viewer) can call these.
Suggestions exclude already-linked candidates / already-applied positions
(handled by the search functions via the relational exclusion join).
"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db import get_db
from app.embeddings.explainer import explain_match
from app.embeddings.search import search_candidates_for_position, search_positions_for_candidate
from app.models import Candidate, Position, PositionRequirement, User
from app.schemas import CandidateMatch, PositionMatch

router = APIRouter(tags=["matches"])


@router.get(
    "/positions/{position_id}/candidate-matches",
    response_model=list[CandidateMatch],
)
async def candidate_matches(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CandidateMatch]:
    scored = await search_candidates_for_position(position_id, db)
    if not scored:
        return []

    cand_ids = [sc.candidate_id for sc in scored]
    result = await db.execute(select(Candidate).where(Candidate.id.in_(cand_ids)))
    by_id = {c.id: c for c in result.scalars().all()}

    return [
        CandidateMatch(
            candidate_id=sc.candidate_id,
            full_name=by_id[sc.candidate_id].full_name,
            headline=by_id[sc.candidate_id].headline or "",
            score=sc.score,
        )
        for sc in scored
        if sc.candidate_id in by_id
    ]


@router.get(
    "/candidates/{candidate_id}/position-matches",
    response_model=list[PositionMatch],
)
async def position_matches(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PositionMatch]:
    scored = await search_positions_for_candidate(candidate_id, db)
    if not scored:
        return []

    pos_ids = [sp.position_id for sp in scored]
    pos_result = await db.execute(
        select(Position)
        .where(Position.id.in_(pos_ids))
        .options(selectinload(Position.requirements))
    )
    positions_by_id = {p.id: p for p in pos_result.scalars().all()}

    cand_result = await db.execute(
        select(Candidate)
        .where(Candidate.id == candidate_id)
        .options(
            selectinload(Candidate.skills),
            selectinload(Candidate.experience),
            selectinload(Candidate.education),
            selectinload(Candidate.certifications),
            selectinload(Candidate.languages),
        )
    )
    candidate = cand_result.scalar_one()

    # fan out explain_match for all matched positions in parallel (≤3)
    async def _explain(sp) -> PositionMatch:
        pos = positions_by_id[sp.position_id]
        explanation, _, _ = await explain_match(candidate, pos, sp.score)
        return PositionMatch(
            position_id=sp.position_id,
            title=pos.title,
            score=sp.score,
            explanation=explanation,
        )

    matches = await asyncio.gather(*[_explain(sp) for sp in scored if sp.position_id in positions_by_id])
    return list(matches)

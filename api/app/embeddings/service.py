"""Embedding write path: upsert and backfill.

Idempotency contract: build text → sha256.  If an existing row has the same
sha, skip (no Bedrock call — cost + reproducibility guard).  Otherwise embed,
upsert with the new vector + text + model + sha + updated_at, flush.

Observability: log id, text length, and token count per embed (Principle 3).
The full embedding_text is stored in the row for inspection/debugging.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.embeddings.text_builder import build_candidate_text, build_position_text, text_sha256
from app.ingest.llm import BedrockClient
from app.models import Candidate, CandidateEmbedding, Position, PositionEmbedding

logger = logging.getLogger(__name__)

_CANDIDATE_EAGER = [
    selectinload(Candidate.skills),
    selectinload(Candidate.experience),
    selectinload(Candidate.education),
    selectinload(Candidate.certifications),
    selectinload(Candidate.languages),
]

_POSITION_EAGER = [
    selectinload(Position.requirements),
]


@dataclass
class BackfillReport:
    candidates_embedded: int
    positions_embedded: int
    skipped: int
    total_tokens: int


async def upsert_candidate_embedding(
    candidate, db: AsyncSession, client: BedrockClient | None = None
) -> bool:
    """Build text → sha.  Skip if sha unchanged.  Embed + upsert otherwise.

    Returns True if (re)embedded, False if skipped.
    """
    text = build_candidate_text(candidate)
    sha = text_sha256(text)

    existing = await db.get(CandidateEmbedding, candidate.id)
    if existing is not None and existing.text_sha256 == sha:
        return False

    client = client or BedrockClient()
    loop = asyncio.get_event_loop()
    vec, tokens = await loop.run_in_executor(None, lambda: client.embed_with_usage(text))

    logger.info(
        "embedded candidate %s len(text)=%d tokens=%d", candidate.id, len(text), tokens
    )

    if existing is None:
        row = CandidateEmbedding(
            candidate_id=candidate.id,
            embedding=vec,
            embedding_text=text,
            embedding_model=client.embed_model_id,
            text_sha256=sha,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        existing.embedding = vec
        existing.embedding_text = text
        existing.embedding_model = client.embed_model_id
        existing.text_sha256 = sha
        existing.updated_at = datetime.now(timezone.utc)

    await db.flush()
    return True


async def upsert_position_embedding(
    position, db: AsyncSession, client: BedrockClient | None = None
) -> bool:
    """Symmetric to upsert_candidate_embedding."""
    text = build_position_text(position)
    sha = text_sha256(text)

    existing = await db.get(PositionEmbedding, position.id)
    if existing is not None and existing.text_sha256 == sha:
        return False

    client = client or BedrockClient()
    loop = asyncio.get_event_loop()
    vec, tokens = await loop.run_in_executor(None, lambda: client.embed_with_usage(text))

    logger.info(
        "embedded position %s len(text)=%d tokens=%d", position.id, len(text), tokens
    )

    if existing is None:
        row = PositionEmbedding(
            position_id=position.id,
            embedding=vec,
            embedding_text=text,
            embedding_model=client.embed_model_id,
            text_sha256=sha,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(row)
    else:
        existing.embedding = vec
        existing.embedding_text = text
        existing.embedding_model = client.embed_model_id
        existing.text_sha256 = sha
        existing.updated_at = datetime.now(timezone.utc)

    await db.flush()
    return True


async def backfill_all(
    db: AsyncSession, client: BedrockClient | None = None
) -> BackfillReport:
    """Embed all candidates + positions; accumulate counts + tokens; log per record."""
    client = client or BedrockClient()

    candidates_result = await db.execute(select(Candidate).options(*_CANDIDATE_EAGER))
    candidates = candidates_result.scalars().all()

    positions_result = await db.execute(select(Position).options(*_POSITION_EAGER))
    positions = positions_result.scalars().all()

    candidates_embedded = 0
    positions_embedded = 0
    skipped = 0
    total_tokens = 0

    # Wrap embed_with_usage to accumulate token counts
    original_embed = client.embed_with_usage

    def tracked_embed(text: str) -> tuple[list[float], int]:
        nonlocal total_tokens
        vec, tokens = original_embed(text)
        total_tokens += tokens
        return vec, tokens

    client.embed_with_usage = tracked_embed  # type: ignore[method-assign]

    for candidate in candidates:
        embedded = await upsert_candidate_embedding(candidate, db, client)
        if embedded:
            candidates_embedded += 1
        else:
            skipped += 1

    for position in positions:
        embedded = await upsert_position_embedding(position, db, client)
        if embedded:
            positions_embedded += 1
        else:
            skipped += 1

    client.embed_with_usage = original_embed  # restore

    return BackfillReport(
        candidates_embedded=candidates_embedded,
        positions_embedded=positions_embedded,
        skipped=skipped,
        total_tokens=total_tokens,
    )

"""Pipeline module — orchestrators for CV and position ingestion.

run_cv_pipeline and run_position_pipeline coordinate all pipeline stages:
  parse → hints → LLM → validate → persist → embed → log

The bedrock_client parameter is injectable for tests; production defaults to
a real BedrockClient instance.  The auto-embed hook is best-effort: failure
logs a warning but does NOT fail ingestion (backfill can fix it later).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .heuristics import extract_hints
from .llm import BedrockClient, call_llm_for_cv, call_llm_for_position
from .logger import log_extraction_run, log_raw_document
from .parsers import parse_cv, parse_position
from .persister import persist_candidate, persist_position
from .types import DocumentKind, ExtractionResult, ExtractionStatus
from .validator import ValidationError, validate_cv_payload, validate_position_payload
from app.models import Candidate, Position

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


async def run_cv_pipeline(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
    bedrock_client=None,
) -> ExtractionResult:
    """Run the full CV extraction pipeline. Returns ExtractionResult.

    ParseError propagates to caller (caller returns 422).
    BedrockError propagates to caller (caller returns 422).
    ValidationError is caught here: failure is logged and FAILED result returned.
    """
    doc = parse_cv(file_bytes, filename)
    hints = extract_hints(doc)
    client = bedrock_client or BedrockClient()
    llm_resp = await call_llm_for_cv(doc, hints, client)

    try:
        payload, warnings, status = validate_cv_payload(llm_resp, hints)
    except ValidationError as e:
        raw_doc_id = await log_raw_document(doc, db)
        run_id = await log_extraction_run(
            raw_doc_id, llm_resp, ExtractionStatus.FAILED, None, [], [str(e)], db
        )
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            document_kind=DocumentKind.CV,
            raw_document_id=raw_doc_id,
            extraction_run_id=run_id,
            errors=[str(e)],
        )

    raw_doc_id = await log_raw_document(doc, db)
    entity_id = await persist_candidate(payload, db, filename)

    # Auto-embed hook — best-effort; failure must NOT fail ingestion
    if entity_id:
        try:
            from sqlalchemy import select
            from app.embeddings.service import upsert_candidate_embedding  # lazy: avoids circular import
            result = await db.execute(
                select(Candidate).where(Candidate.id == entity_id).options(*_CANDIDATE_EAGER)
            )
            candidate = result.scalar_one()
            await upsert_candidate_embedding(candidate, db)
        except Exception as exc:
            logger.warning("auto-embed failed for candidate %s: %s", entity_id, exc)

    run_id = await log_extraction_run(
        raw_doc_id, llm_resp, status, entity_id, warnings, [], db
    )
    return ExtractionResult(
        status=status,
        document_kind=DocumentKind.CV,
        raw_document_id=raw_doc_id,
        extraction_run_id=run_id,
        entity_id=entity_id,
        warnings=warnings,
        input_tokens=llm_resp.input_tokens,
        output_tokens=llm_resp.output_tokens,
        model_id=llm_resp.model_id,
    )


async def run_position_pipeline(
    file_bytes: bytes,
    filename: str,
    db: AsyncSession,
    bedrock_client=None,
) -> ExtractionResult:
    """Run the full position extraction pipeline. Returns ExtractionResult."""
    doc = parse_position(file_bytes, filename)
    hints = extract_hints(doc)
    client = bedrock_client or BedrockClient()
    llm_resp = await call_llm_for_position(doc, hints, client)

    try:
        payload, warnings, status = validate_position_payload(llm_resp, hints)
    except ValidationError as e:
        raw_doc_id = await log_raw_document(doc, db)
        run_id = await log_extraction_run(
            raw_doc_id, llm_resp, ExtractionStatus.FAILED, None, [], [str(e)], db
        )
        return ExtractionResult(
            status=ExtractionStatus.FAILED,
            document_kind=DocumentKind.POSITION,
            raw_document_id=raw_doc_id,
            extraction_run_id=run_id,
            errors=[str(e)],
        )

    raw_doc_id = await log_raw_document(doc, db)
    entity_id = await persist_position(payload, db)

    # Auto-embed hook — best-effort; failure must NOT fail ingestion
    if entity_id:
        try:
            from sqlalchemy import select
            from app.embeddings.service import upsert_position_embedding  # lazy: avoids circular import
            result = await db.execute(
                select(Position).where(Position.id == entity_id).options(*_POSITION_EAGER)
            )
            position = result.scalar_one()
            await upsert_position_embedding(position, db)
        except Exception as exc:
            logger.warning("auto-embed failed for position %s: %s", entity_id, exc)

    run_id = await log_extraction_run(
        raw_doc_id, llm_resp, status, entity_id, warnings, [], db
    )
    return ExtractionResult(
        status=status,
        document_kind=DocumentKind.POSITION,
        raw_document_id=raw_doc_id,
        extraction_run_id=run_id,
        entity_id=entity_id,
        warnings=warnings,
        input_tokens=llm_resp.input_tokens,
        output_tokens=llm_resp.output_tokens,
        model_id=llm_resp.model_id,
    )

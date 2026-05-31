"""Pipeline observability — write raw_documents and extraction_runs to DB.

Both functions flush without committing; the orchestrator controls the outer
transaction and the endpoint calls commit once, atomically.

Note: uploaded_at / created_at are passed explicitly as Python datetime objects.
SQLite cannot evaluate 'now()' server_default literals; Postgres accepts explicit
values too, so this is safe in both environments.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExtractionRun
from app.models import RawDocument as RawDocumentModel

from .types import ExtractionStatus, LLMResponse, RawDocument


async def log_raw_document(doc: RawDocument, db: AsyncSession) -> int:
    """Insert a raw_documents row and return its generated id."""
    row = RawDocumentModel(
        filename=doc.filename,
        format=doc.format.value,
        document_kind=doc.kind.value,
        raw_text=doc.raw_text,
        char_count=doc.char_count,
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row.id


async def log_extraction_run(
    raw_doc_id: int,
    llm_response: LLMResponse,
    status: ExtractionStatus,
    entity_id: str | None,
    warnings: list[str],
    errors: list[str],
    db: AsyncSession,
) -> int:
    """Insert an extraction_runs row and return its generated id."""
    row = ExtractionRun(
        raw_document_id=raw_doc_id,
        model_id=llm_response.model_id,
        prompt_version=llm_response.prompt_version,
        prompt_text=llm_response.prompt_text,
        raw_llm_output=llm_response.raw_json_str,
        status=status.value,
        entity_id=entity_id,
        errors=errors,
        warnings=warnings,
        input_tokens=llm_response.input_tokens,
        output_tokens=llm_response.output_tokens,
        latency_ms=llm_response.latency_ms,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row.id

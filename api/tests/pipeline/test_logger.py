"""DB-backed unit tests for pipeline/logger.py.

Uses the seeded_db fixture (SQLite in-memory). ExtractionRun.errors and
.warnings are patched from ARRAY(Text) to JSON() in conftest.py.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import ExtractionRun
from app.models import RawDocument as RawDocumentModel
from app.pipeline.logger import log_extraction_run, log_raw_document
from app.pipeline.types import DocumentKind, ExtractionStatus, LLMResponse, ParseFormat, RawDocument


def _raw_doc(filename: str = "test.pdf") -> RawDocument:
    return RawDocument(
        filename=filename,
        format=ParseFormat.PDF,
        kind=DocumentKind.CV,
        raw_text="Alice Smith\nSoftware Engineer",
        char_count=27,
    )


def _llm_resp() -> LLMResponse:
    return LLMResponse(
        model_id="test-model",
        prompt_version="cv-v1",
        prompt_text="[SYSTEM]\n...\n[USER]\n...",
        raw_json_str='{"full_name": "Alice Smith"}',
        input_tokens=100,
        output_tokens=50,
        latency_ms=200,
    )


# ---------------------------------------------------------------------------
# log_raw_document
# ---------------------------------------------------------------------------

async def test_log_raw_document_returns_positive_id(seeded_db):
    async with seeded_db() as db:
        row_id = await log_raw_document(_raw_doc(), db)
        await db.commit()

    assert row_id > 0


async def test_log_raw_document_row_queryable_by_id(seeded_db):
    async with seeded_db() as db:
        row_id = await log_raw_document(_raw_doc("cv_upload.pdf"), db)
        await db.commit()

    async with seeded_db() as db:
        result = await db.execute(
            select(RawDocumentModel).where(RawDocumentModel.id == row_id)
        )
        row = result.scalar_one()
        assert row.filename == "cv_upload.pdf"
        assert row.char_count == 27
        assert row.document_kind == "cv"
        assert row.format == "pdf"


# ---------------------------------------------------------------------------
# log_extraction_run
# ---------------------------------------------------------------------------

async def test_log_extraction_run_returns_positive_id(seeded_db):
    async with seeded_db() as db:
        raw_doc_id = await log_raw_document(_raw_doc(), db)
        run_id = await log_extraction_run(
            raw_doc_id=raw_doc_id,
            llm_response=_llm_resp(),
            status=ExtractionStatus.SUCCESS,
            entity_id="cv_abc12345",
            warnings=[],
            errors=[],
            db=db,
        )
        await db.commit()

    assert run_id > 0


async def test_log_extraction_run_failed_status_and_errors_persisted(seeded_db):
    async with seeded_db() as db:
        raw_doc_id = await log_raw_document(_raw_doc(), db)
        run_id = await log_extraction_run(
            raw_doc_id=raw_doc_id,
            llm_response=_llm_resp(),
            status=ExtractionStatus.FAILED,
            entity_id=None,
            warnings=[],
            errors=["full_name is required but missing or empty"],
            db=db,
        )
        await db.commit()

    async with seeded_db() as db:
        result = await db.execute(
            select(ExtractionRun).where(ExtractionRun.id == run_id)
        )
        row = result.scalar_one()
        assert row.status == "failed"
        assert row.entity_id is None
        assert "full_name" in row.errors[0]
        assert row.warnings == []


async def test_log_extraction_run_warnings_stored(seeded_db):
    async with seeded_db() as db:
        raw_doc_id = await log_raw_document(_raw_doc(), db)
        run_id = await log_extraction_run(
            raw_doc_id=raw_doc_id,
            llm_response=_llm_resp(),
            status=ExtractionStatus.PARTIAL,
            entity_id="cv_partial1",
            warnings=["experience[0].start_year: coerced from str '2019' to int"],
            errors=[],
            db=db,
        )
        await db.commit()

    async with seeded_db() as db:
        result = await db.execute(
            select(ExtractionRun).where(ExtractionRun.id == run_id)
        )
        row = result.scalar_one()
        assert row.status == "partial"
        assert row.entity_id == "cv_partial1"
        assert len(row.warnings) == 1
        assert "start_year" in row.warnings[0]

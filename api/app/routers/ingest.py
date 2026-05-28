"""Ingest endpoints — POST /api/ingest/cv, POST /api/ingest/position.

Requires admin or recruiter role. Accepts multipart/form-data file upload,
runs the extraction pipeline, commits results, and returns IngestResponse.
ParseError and any exception from the LLM layer surface as HTTP 422.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_role
from app.db import get_db
from app.models import User
from app.pipeline import run_cv_pipeline, run_position_pipeline
from app.pipeline.parsers import ParseError
from app.schemas import IngestResponse

router = APIRouter(tags=["ingest"])

_ALLOWED_ROLES = ("admin", "recruiter")


@router.post("/ingest/cv", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_cv(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(*_ALLOWED_ROLES)),
) -> IngestResponse:
    file_bytes = await file.read()
    try:
        result = await run_cv_pipeline(file_bytes, file.filename or "", db)
    except ParseError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    await db.commit()
    return IngestResponse(
        status=result.status.value,
        entity_id=result.entity_id,
        run_id=result.extraction_run_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        warnings=result.warnings,
        errors=result.errors,
    )


@router.post("/ingest/position", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_position(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(*_ALLOWED_ROLES)),
) -> IngestResponse:
    file_bytes = await file.read()
    try:
        result = await run_position_pipeline(file_bytes, file.filename or "", db)
    except ParseError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    await db.commit()
    return IngestResponse(
        status=result.status.value,
        entity_id=result.entity_id,
        run_id=result.extraction_run_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        warnings=result.warnings,
        errors=result.errors,
    )

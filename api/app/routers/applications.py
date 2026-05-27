from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import Application, Candidate, Position, User
from app.schemas import Application as ApplicationSchema, ApplicationCreate

router = APIRouter(tags=["applications"])


def _to_schema(a: Application) -> ApplicationSchema:
    return ApplicationSchema(
        id=a.id,
        candidate_id=a.candidate_id,
        position_id=a.position_id,
        status=a.status,
    )


@router.get("/applications", response_model=list[ApplicationSchema])
async def list_applications(
    candidate_id: Optional[str] = Query(None, alias="candidateId"),
    position_id: Optional[str] = Query(None, alias="positionId"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ApplicationSchema]:
    stmt = select(Application)
    if candidate_id:
        stmt = stmt.where(Application.candidate_id == candidate_id)
    if position_id:
        stmt = stmt.where(Application.position_id == position_id)
    result = await db.execute(stmt)
    return [_to_schema(a) for a in result.scalars().all()]


@router.post("/applications", response_model=ApplicationSchema, status_code=status.HTTP_201_CREATED)
async def create_application(
    body: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "recruiter")),
) -> ApplicationSchema:
    candidate = await db.get(Candidate, body.candidate_id)
    if candidate is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

    position = await db.get(Position, body.position_id)
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    app = Application(
        id=f"app-{uuid.uuid4().hex[:8]}",
        candidate_id=body.candidate_id,
        position_id=body.position_id,
        status=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(app)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application already exists")
    await db.refresh(app)
    return _to_schema(app)


@router.delete("/applications/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "recruiter")),
) -> None:
    app = await db.get(Application, application_id)
    if app is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    await db.delete(app)
    await db.commit()

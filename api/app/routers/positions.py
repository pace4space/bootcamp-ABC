from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models import Position, PositionRequirement, User
from app.schemas import (
    Position as PositionSchema,
    PositionPatch,
    Requirements,
    SourceEmail,
)

router = APIRouter(tags=["positions"])

_EAGER = [selectinload(Position.requirements)]


def _to_schema(p: Position) -> PositionSchema:
    must = [r.text for r in p.requirements if r.type == "must_have"]
    nice = [r.text for r in p.requirements if r.type == "nice_to_have"]
    return PositionSchema(
        id=p.id,
        title=p.title,
        status=p.status,
        hiring_manager_email=p.hiring_manager_email or "",
        description=p.description or "",
        requirements=Requirements(must_have=must, nice_to_have=nice) if p.requirements else None,
        location=p.location,
        seniority=p.seniority,
        salary_range=p.salary_range,
        source_document=SourceEmail(
            file_name=p.source_document_filename or "",
            path=p.source_document_path or "",
        ),
    )


@router.get("/positions", response_model=list[PositionSchema])
async def list_positions(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PositionSchema]:
    result = await db.execute(
        select(Position)
        .where(Position.status == "Open")
        .options(*_EAGER)
        .order_by(Position.title)
    )
    return [_to_schema(p) for p in result.scalars().all()]


@router.get("/positions/{position_id}", response_model=PositionSchema)
async def get_position(
    position_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> PositionSchema:
    result = await db.execute(
        select(Position).where(Position.id == position_id).options(*_EAGER)
    )
    position = result.scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")
    return _to_schema(position)


@router.patch("/positions/{position_id}", response_model=PositionSchema)
async def patch_position(
    position_id: str,
    body: PositionPatch,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "recruiter")),
) -> PositionSchema:
    result = await db.execute(
        select(Position).where(Position.id == position_id).options(*_EAGER)
    )
    position = result.scalar_one_or_none()
    if position is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Position not found")

    patch = body.model_dump(exclude_unset=True)

    if "requirements" in patch:
        reqs = patch.pop("requirements")
        await db.execute(
            delete(PositionRequirement).where(PositionRequirement.position_id == position_id)
        )
        if reqs:
            for i, text in enumerate(reqs.get("must_have") or []):
                db.add(PositionRequirement(position_id=position_id, type="must_have", text=text, sort_order=i))
            for i, text in enumerate(reqs.get("nice_to_have") or []):
                db.add(PositionRequirement(position_id=position_id, type="nice_to_have", text=text, sort_order=i))

    for field, value in patch.items():
        setattr(position, field, value)

    await db.commit()

    result = await db.execute(
        select(Position).where(Position.id == position_id).options(*_EAGER)
    )
    return _to_schema(result.scalar_one())

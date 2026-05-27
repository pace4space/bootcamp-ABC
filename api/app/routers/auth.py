from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_current_user, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserInfo

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> LoginResponse:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return LoginResponse(token=token, user=UserInfo(id=user.id, email=user.email, role=user.role))


@router.get("/auth/me", response_model=UserInfo)
async def me(current_user: User = Depends(get_current_user)) -> UserInfo:
    return UserInfo(id=current_user.id, email=current_user.email, role=current_user.role)

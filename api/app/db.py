"""Async database session factory for Hellio HR API.

Reads DATABASE_URL from the environment. In production this points at Postgres
via asyncpg (postgresql+asyncpg://...). In tests it points at an in-memory
SQLite database via aiosqlite (sqlite+aiosqlite:///:memory:).

Usage in FastAPI routes:

    from app.db import get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    @router.get("/example")
    async def example(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(MyModel))
        ...
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    # Default allows the API container to start without crashing at import
    # time even when DATABASE_URL is absent (e.g., during alembic autogenerate
    # from a dev workstation without a running DB).
    "postgresql+asyncpg://hellio:hellio@localhost:5432/hellio",
)

engine = create_async_engine(
    DATABASE_URL,
    # Echo SQL to stdout in debug mode; set APP_ENV=production to silence it.
    echo=os.environ.get("APP_ENV", "development") == "development",
    # Pool sizing — these are the asyncpg defaults; explicit for clarity.
    pool_size=5,
    max_overflow=10,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # avoid lazy-load errors after commit in async context
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session; roll back on exception, close on exit."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

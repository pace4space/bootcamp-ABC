"""Alembic migration environment for Hellio HR API.

Uses the async engine pattern required by asyncpg. Alembic itself is
synchronous, so we drive the async connection with asyncio.run() and
conn.run_sync(do_run_migrations).

The DATABASE_URL is read from the environment variable of the same name,
falling back to the value in alembic.ini only when the env var is absent.

Run from the api/ directory:
    alembic upgrade head
    alembic downgrade base
    alembic revision --autogenerate -m "add foo table"
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Import the ORM metadata so Alembic can detect schema differences.
# `alembic check` and `--autogenerate` both rely on Base.metadata.
# ---------------------------------------------------------------------------
from app.models import Base  # noqa: E402

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values in alembic.ini.
# ---------------------------------------------------------------------------
config = context.config

# Apply Python logging configuration from alembic.ini.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata object that --autogenerate will compare against.
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Resolve the database URL.
# Priority: DATABASE_URL env var > alembic.ini sqlalchemy.url
# ---------------------------------------------------------------------------
def _get_url() -> str:
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


# ---------------------------------------------------------------------------
# Offline mode (generates SQL without a live connection).
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Emit migration SQL to stdout without connecting to the database.

    Useful for generating SQL scripts to review or run manually.
    """
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode (connects to the real database and runs migrations).
# ---------------------------------------------------------------------------
def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    """Inner function that alembic calls inside conn.run_sync()."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Create an async engine and drive the sync migration inside run_sync()."""
    url = _get_url()
    connectable = create_async_engine(url, echo=False)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

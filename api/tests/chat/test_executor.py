"""Segment 05 tests — query executor (read-only, SQLite path)."""
from __future__ import annotations

import json

import pytest

from app.chat.executor import execute_readonly


@pytest.mark.asyncio
async def test_select_returns_rows_and_columns(seeded_db):
    async with seeded_db() as session:
        result = await execute_readonly(
            "SELECT id, full_name FROM candidates WHERE status='Active'", session
        )
    assert result.ok
    assert result.columns == ["id", "full_name"]
    assert result.row_count >= 2
    assert all(isinstance(r, dict) for r in result.rows)


@pytest.mark.asyncio
async def test_anti_join_open_positions_without_candidates(seeded_db):
    sql = (
        "SELECT p.id FROM positions p "
        "LEFT JOIN applications a ON a.position_id = p.id "
        "WHERE p.status = 'Open' AND a.id IS NULL"
    )
    async with seeded_db() as session:
        result = await execute_readonly(sql, session)
    assert result.ok
    assert isinstance(result.row_count, int)


@pytest.mark.asyncio
async def test_zero_rows_has_columns(seeded_db):
    async with seeded_db() as session:
        result = await execute_readonly(
            "SELECT id FROM candidates WHERE id='nope'", session
        )
    assert result.ok
    assert result.row_count == 0
    assert result.columns == ["id"]


@pytest.mark.asyncio
async def test_bad_column_is_graceful(seeded_db):
    async with seeded_db() as session:
        result = await execute_readonly(
            "SELECT nonexistent FROM candidates", session
        )
    assert not result.ok
    assert result.error


@pytest.mark.asyncio
async def test_readonly_blocks_write(seeded_db):
    async with seeded_db() as session:
        result = await execute_readonly(
            "UPDATE candidates SET status='x'", session
        )
        assert not result.ok
        assert result.error
        error_lower = result.error.lower()
        assert "read" in error_lower or "not authorized" in error_lower

        # PRAGMA query_only = OFF was restored in the finally; subsequent reads must work
        followup = await execute_readonly(
            "SELECT id FROM candidates LIMIT 1", session
        )
    assert followup.ok


@pytest.mark.asyncio
async def test_datetime_is_jsonable(seeded_db):
    async with seeded_db() as session:
        result = await execute_readonly(
            "SELECT created_at FROM applications LIMIT 1", session
        )
    assert result.ok
    assert result.row_count == 1
    # json.dumps must not raise — datetime/Decimal coercion is the contract
    serialized = json.dumps(result.rows)
    assert serialized

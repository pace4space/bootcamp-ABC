"""Segment 04 tests — SQL safety guard. Treat a red here as a release blocker."""
from __future__ import annotations

import pytest

from app.query.guard import UnsafeSQLError, validate_sql


# ---------------------------------------------------------------------------
# Must REJECT
# ---------------------------------------------------------------------------

def test_rejects_drop():
    with pytest.raises(UnsafeSQLError):
        validate_sql("DROP TABLE candidates")


def test_rejects_delete():
    with pytest.raises(UnsafeSQLError):
        validate_sql("DELETE FROM candidates")


def test_rejects_update():
    with pytest.raises(UnsafeSQLError):
        validate_sql("UPDATE candidates SET status='x'")


def test_rejects_insert():
    with pytest.raises(UnsafeSQLError):
        validate_sql("INSERT INTO candidates VALUES (1)")


def test_rejects_trailing_delete():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT 1; DELETE FROM candidates")


def test_rejects_multiple_statements():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT 1; SELECT 2")


def test_rejects_comment_hidden_dml():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT 1 /* x */; DROP TABLE candidates --")


def test_rejects_select_into():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SELECT * INTO evil FROM candidates")


def test_rejects_set():
    with pytest.raises(UnsafeSQLError):
        validate_sql("SET ROLE admin")


def test_rejects_pragma():
    with pytest.raises(UnsafeSQLError):
        validate_sql("PRAGMA table_info(users)")


def test_rejects_empty():
    with pytest.raises(UnsafeSQLError):
        validate_sql("   ")


def test_rejects_non_select_leading():
    with pytest.raises(UnsafeSQLError):
        validate_sql("EXPLAIN ANALYZE SELECT 1")


# ---------------------------------------------------------------------------
# Must ACCEPT
# ---------------------------------------------------------------------------

def test_accepts_plain_select():
    result = validate_sql("SELECT id FROM candidates")
    assert "LIMIT 100" in result


def test_accepts_with_cte():
    result = validate_sql("WITH x AS (SELECT 1) SELECT * FROM x")
    assert result  # accepted — just check it returns without error


def test_accepts_existing_limit_unchanged():
    result = validate_sql("SELECT id FROM candidates LIMIT 5")
    assert result.upper().count("LIMIT") == 1


def test_strips_trailing_semicolon():
    result = validate_sql("SELECT 1;")
    assert ";" not in result


def test_literal_with_keyword_not_rejected():
    result = validate_sql("SELECT id FROM candidates WHERE city ILIKE '%Delete City%'")
    assert result  # string-literal blanking prevents false positive


def test_count_query_accepted():
    result = validate_sql("SELECT COUNT(*) FROM positions WHERE status='Open'")
    assert result  # LIMIT appended is harmless for COUNT

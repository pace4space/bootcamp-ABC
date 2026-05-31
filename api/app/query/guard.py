"""Deterministic SQL safety gate — validates LLM-generated SQL before execution."""
from __future__ import annotations

import re


class UnsafeSQLError(Exception):
    """Raised when generated SQL is not a single safe read-only SELECT."""

    def __init__(self, reason: str, sql: str):
        self.reason = reason
        self.sql = sql
        super().__init__(f"{reason}: {sql!r}")


_BLOCKLIST = (
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "COPY", "MERGE",
    "REPLACE", "EXEC", "EXECUTE", "CALL", "VACUUM", "REINDEX", "SET", "INTO",
)
_LIMIT_CAP = 100


def validate_sql(sql: str) -> str:
    raw = sql  # keep original for error messages

    # 1. strip comments: block /* ... */ then line -- ... to EOL
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    s = re.sub(r"--[^\n]*", " ", s)
    s = s.strip()

    # 2. one statement only: drop a single trailing ';' then reject any remaining ';'
    if s.endswith(";"):
        s = s[:-1].strip()
    if ";" in s:
        raise UnsafeSQLError("multiple statements are not allowed", raw)

    # 3. non-empty
    if not s:
        raise UnsafeSQLError("empty query", raw)

    # 4. must start with SELECT or WITH (CTE → SELECT)
    first = re.match(r"\s*(\w+)", s)
    if not first or first.group(1).upper() not in ("SELECT", "WITH"):
        raise UnsafeSQLError("only SELECT/WITH queries are allowed", raw)

    # 5. keyword blocklist — scan structure, not string literals.
    #    Blank out single-quoted literals so '%Delete Inc%' is not a false positive.
    scan = re.sub(r"'(?:[^']|'')*'", "''", s)
    for kw in _BLOCKLIST:
        if re.search(rf"\b{kw}\b", scan, flags=re.IGNORECASE):
            raise UnsafeSQLError(f"forbidden keyword: {kw}", raw)

    # 6. cap result size if the model didn't (harmless for COUNT/aggregate queries)
    if not re.search(r"\bLIMIT\b", scan, flags=re.IGNORECASE):
        s = f"{s} LIMIT {_LIMIT_CAP}"

    return s

# Ex4 — Segment 04: SQL Safety Guard

**Depends on:** nothing (pure function). **Blocks:** 07 (orchestrator calls `validate_sql`).

## Goal

`query/guard.py` is the deterministic gate that turns *untrusted LLM SQL* into *SQL we are willing
to execute*. Hand-rolled (no `sqlglot`). It either returns a sanitized, LIMIT-capped SQL string or
raises `UnsafeSQLError`. **The prompt asks for a SELECT; the guard enforces it.** This is the
primary safety layer; the read-only transaction (05) and the schema allowlist (02) are the others.

## The algorithm (implement exactly; order matters)

```python
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
    raw = sql                                   # keep original for error messages
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

    # 5. keyword blocklist — scan STRUCTURE, not string literals.
    #    Blank out single-quoted literals so a value like '%Delete Inc%' is not a false positive.
    scan = re.sub(r"'(?:[^']|'')*'", "''", s)
    for kw in _BLOCKLIST:
        if re.search(rf"\b{kw}\b", scan, flags=re.IGNORECASE):
            raise UnsafeSQLError(f"forbidden keyword: {kw}", raw)

    # 6. cap result size if the model didn't (harmless for COUNT/aggregate queries)
    if not re.search(r"\bLIMIT\b", scan, flags=re.IGNORECASE):
        s = f"{s} LIMIT {_LIMIT_CAP}"

    return s
```

`import re` at the top.

## Design notes (own every line)

- **Why blank string literals before the blocklist scan?** A legitimate question — *"candidates who
  worked at Delete Inc"* — could yield `... ILIKE '%Delete Inc%'`. Without blanking, the bare `DELETE`
  substring trips the blocklist (false positive). DML keywords cannot live *inside* a string literal
  and still execute, so blanking literals removes false positives without weakening the gate. Lesson:
  **validate the SQL structure, not the data values.**
- **Why blocklist `SET` and `INTO`?** `SET` blocks session-state changes; `INTO` blocks
  `SELECT … INTO new_table` (a stealth write). `PRAGMA`/`ATTACH` block SQLite-specific escape hatches.
- **Why allow `WITH`?** CTEs are read-only and the few-shot may use them; a `WITH … DELETE` is still
  caught by the `DELETE` keyword. So `WITH` is safe to lead with.
- **Stacking defenses:** even if a write slipped past (it won't), the executor (05) runs in a
  read-only transaction and the DB itself rejects it. The guard is necessary, not solely sufficient.
- **Known limitation (document, don't fix):** comment-stripping is regex-based, not a full lexer, so a
  `--` inside a string literal is over-stripped. For generated analytical SELECTs this never matters;
  a full parser (`sqlglot`) would be the upgrade if this module ever accepted human-written SQL.

## Tests (`api/tests/query/test_guard.py`) — write first. This is the most important test file.

**Must REJECT (each `pytest.raises(UnsafeSQLError)`):**

| Case | Input |
|------|-------|
| `test_rejects_drop` | `DROP TABLE candidates` |
| `test_rejects_delete` | `DELETE FROM candidates` |
| `test_rejects_update` | `UPDATE candidates SET status='x'` |
| `test_rejects_insert` | `INSERT INTO candidates VALUES (1)` |
| `test_rejects_trailing_delete` | `SELECT 1; DELETE FROM candidates` |
| `test_rejects_multiple_statements` | `SELECT 1; SELECT 2` |
| `test_rejects_comment_hidden_dml` | `SELECT 1 /* x */; DROP TABLE candidates --` |
| `test_rejects_select_into` | `SELECT * INTO evil FROM candidates` |
| `test_rejects_set` | `SET ROLE admin` |
| `test_rejects_pragma` | `PRAGMA table_info(users)` |
| `test_rejects_empty` | `   ` |
| `test_rejects_non_select_leading` | `EXPLAIN ANALYZE SELECT 1` (EXPLAIN not in SELECT/WITH) |

**Must ACCEPT (returns a string):**

| Case | Input | Assertion |
|------|-------|-----------|
| `test_accepts_plain_select` | `SELECT id FROM candidates` | returns SQL; ends with `LIMIT 100` |
| `test_accepts_with_cte` | `WITH x AS (SELECT 1) SELECT * FROM x` | returned, accepted |
| `test_accepts_existing_limit_unchanged` | `SELECT id FROM candidates LIMIT 5` | no second LIMIT appended (assert `.count("LIMIT") == 1` on uppercased) |
| `test_strips_trailing_semicolon` | `SELECT 1;` | accepted; no `;` in result |
| `test_literal_with_keyword_not_rejected` | `SELECT id FROM candidates WHERE city ILIKE '%Delete City%'` | accepted (string-literal blanking) |
| `test_count_query_accepted` | `SELECT COUNT(*) FROM positions WHERE status='Open'` | accepted (LIMIT appended, harmless) |

## Verification
- `cd api && .venv/bin/pytest tests/query/test_guard.py -q` → all green (this file alone is the
  safety proof; treat a red here as a release blocker).

# Ex4 — Segment 09: Testing Strategy

**Depends on:** 01–08. This segment is partly written *alongside* each module (test-first), and
partly a final integration + live-demo pass.

## Layering (mirror `api/tests/pipeline/`)

```
api/tests/query/
  __init__.py
  test_types_models.py     (01) QueryRun round-trip on SQLite, no ARRAY patch
  test_generator.py        (03) fence strip, history fold, tokens — FakeBedrock injected
  test_guard.py            (04) the safety matrix — the single most important file
  test_executor.py         (05) read-only enforcement, columns/rows, graceful failure
  test_answerer.py         (06) grounding, empty short-circuit, conversation entries
  test_chat_endpoint.py    (07) full loop over HTTP, Bedrock monkeypatched
```

Bedrock is **mocked in every automated test** (same rule as Ex3 — no network, no credentials, no
cost in CI). The four *real* questions are verified once, manually, against live Nova + Postgres.

## conftest change (one line — low risk)

`api/tests/query/` reuses the main fixtures (`client`, `auth_headers`, `viewer_headers`, `seeded_db`)
from `api/tests/conftest.py`. The only change needed there: add `QueryRun` to the
`from app.models import (...)` block so `Base.metadata.create_all` builds the `query_runs` table.

**No `StaticPool` and no `.type = JSON()` patch are needed**, because (a) `query_runs` has no ARRAY
columns (segment 01), and (b) the executor's SQLite branch reuses the *request* connection
(`await db.connection()`), so there is no second-connection in-memory-DB problem (segment 05).
Run the full suite after the edit to confirm Ex3's 101 stay green.

## The endpoint test — monkeypatch target (known project pattern)

`generator.py` and `answerer.py` each do `from app.pipeline.llm import BedrockClient`, binding the
name into **their own** namespaces. Per the project's monkeypatch rule, patch the names where they
were imported, not the definition site:

- patch `app.query.generator.BedrockClient`
- patch `app.query.answerer.BedrockClient`

```python
class FakeBedrock:
    model_id = "amazon.nova-lite-v1:0"
    def __init__(self, *a, **k): pass
    # generator path:
    def converse(self, system, user):
        return FakeBedrock.SQL, 30, 12
    # answerer path:
    def converse_messages(self, system, messages):
        return "Here are the active candidates: Alice Tester, Bob Tester.", 18, 8

# default SQL is SQLite-safe (no ILIKE) because we control the mock:
FakeBedrock.SQL = "SELECT id, full_name FROM candidates WHERE status = 'Active'"
```

```python
@pytest.fixture
def mock_bedrock(monkeypatch):
    monkeypatch.setattr("app.query.generator.BedrockClient", FakeBedrock)
    monkeypatch.setattr("app.query.answerer.BedrockClient", FakeBedrock)
```

### `test_chat_endpoint.py` cases

| Test | Setup | Assertion |
|------|-------|-----------|
| `test_success_grounded` | mock returns the Active-candidates SELECT | 200; `status=='success'`; `answer` non-empty; `sql` contains `SELECT`; `trace.rowCount >= 2`; `'full_name' in trace.columns`; `runId` present |
| `test_camelcase_serialization` | same | response JSON has keys `rowCount`, `runId` (camelCase via `_CONFIG`) |
| `test_query_run_persisted` | same | after the call, a `query_runs` row exists with `status='success'` and matching `row_count` |
| `test_viewer_can_chat` | `viewer_headers` | 200 (read-only → viewer allowed) |
| `test_unauthenticated_401` | no auth header | 401 |
| `test_unsafe_sql_returns_200_with_status` | set `FakeBedrock.SQL = "DROP TABLE candidates"` | 200; `status=='unsafe'`; `error` non-empty; `query_runs` row `status='unsafe'`; **table still exists** (guard blocked it) |
| `test_sql_error_returns_200` | `FakeBedrock.SQL = "SELECT nope FROM candidates"` | 200; `status=='sql_error'`; `error` mentions the bad column; `query_runs` row `status='sql_error'` |
| `test_llm_error_returns_422` | make `converse` raise `BedrockError` (subclass FakeBedrock or a 2nd fake) | 422; detail has `error` + `suggestion`; a `query_runs` row with `status='llm_error'` was still written |
| `test_multi_turn_history_accepted` | pass `history=[{role:'user',...},{role:'assistant',...}]` | 200; no error (history threaded through without breaking) |

> Reset `FakeBedrock.SQL` between tests that mutate it (use a fixture or set it inside each test).

## The four required questions — live demo (Ex3 Step 9 style)

Automated tests mock the LLM, so the *generation quality* of the four required questions is verified
**manually** against real Nova + Postgres, and recorded in `docs/ex4/submission-ex4.md`:

1. `list open position counts by department` → expect a `GROUP BY` (with the seniority/location
   substitution stated in the answer, since there is no department column — see segment 02).
2. `which positions do not have any candidate` → `LEFT JOIN applications … WHERE … IS NULL`.
3. `which positions have more than 2 candidates` → `GROUP BY … HAVING COUNT(...) > 2`.
4. `list all candidates with kubernetes experience` → `JOIN candidate_skills … ILIKE '%kubernetes%'`.

For each, capture in the submission doc: the question, the generated SQL, the row count, and the
grounded answer. This is the demo evidence the exercise requires ("must be demo-able with realistic
questions").

### Live demo runbook
```
docker compose up -d            # Postgres
cd api && alembic upgrade head  # applies 0003_query_runs
# ensure AWS creds + BEDROCK_MODEL_ID in env (Nova Lite default)
.venv/bin/uvicorn app.main:app --reload
# obtain a token via POST /api/auth/login, then POST /api/chat for each question
```

## Definition of done (Ex4)
- `cd api && .venv/bin/pytest -q` → **all green** (101 prior + the new `tests/query/` suite).
- `tsc -b` + `npm run build` clean; `/chat` works in `npm run dev` with multi-turn + trace panel.
- `docs/ex4/submission-ex4.md` records the four live questions (SQL + rows + grounded answer).
- `query_runs` rows present after a live session (observability proven).
- PROGRESS.md + JOURNAL.md updated; commits are per-segment and each leaves the app demo-able.

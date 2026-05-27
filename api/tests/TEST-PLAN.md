# Hellio HR — Exercise 2 API Test Plan

> Ground truth for `api/tests/`. Every test case maps to `docs/api-contract.md`.
> Implementation order: conftest → test_health → test_auth → test_candidates
> → test_positions → test_applications.

---

## Design Decisions

**SQLite in-memory** for all tests — no container needed, `pytest` runs standalone.
`app.dependency_overrides[get_db]` injects the test session; routers never see Postgres.

**SQLite caveat**: `ARRAY(Text)` (highlights) is Postgres-only. conftest patches that
column to `Text` before `create_all`. CHECK constraints are not enforced by SQLite;
Pydantic enforces them at the API boundary (tested via 422 assertions).

**Function-scope fixtures** — each test gets a fresh in-memory DB. No test-order deps.

**Minimal seed** — purpose-built IDs (cv_t01, pos_t01, app_t01) avoid coupling to
production data and keep filter assertions unambiguous.

---

## Seed Data

### Candidates
| id | fullName | status | experience startYears |
|---|---|---|---|
| `cv_t01` | Alice Tester | Active | 2022 (endYear null), 2020 (endYear 2021) |
| `cv_t02` | Bob Tester | Active | 2021 (endYear null) |
| `cv_t99` | Carol Archived | Archived | 2019 (endYear null) |

`cv_t01` has two experience rows to verify descending sort.

### Positions
| id | title | status | requirements |
|---|---|---|---|
| `pos_t01` | Test Position Open A | Open | present (mustHave + niceToHave) |
| `pos_t02` | Test Position Open B | Open | absent (null) |
| `pos_t03` | Test Position Closed | Closed | present |

### Applications
| id | candidateId | positionId | status |
|---|---|---|---|
| `app_t01` | cv_t01 | pos_t01 | Waiting |
| `app_t02` | cv_t02 | pos_t01 | null |
| `app_t03` | cv_t01 | pos_t02 | Rejected |

### Users
| email | password | role |
|---|---|---|
| admin@hellio.com | admin123 | admin |
| recruiter@hellio.com | recruiter123 | recruiter |
| viewer@hellio.com | viewer123 | viewer |

---

## conftest.py Fixtures

| Fixture | Scope | What it does |
|---|---|---|
| `engine` | function | `sqlite+aiosqlite://` engine; no pool_size/max_overflow (invalid for SQLite); `create_all` on setup, `drop_all` on teardown |
| `seeded_db` | function | Inserts all seed rows above; yields AsyncSession |
| `client` | function | `AsyncClient(app=app)`; injects seeded session via `dependency_overrides[get_db]` |
| `auth_headers` | function | POSTs login as admin@hellio.com; returns `{"Authorization": "Bearer <token>"}` |
| `recruiter_headers` | function | Same for recruiter@hellio.com |
| `viewer_headers` | function | Same for viewer@hellio.com |

---

## test_health.py

### test_health_returns_ok
**Fixtures**: client  
**Action**: GET /api/health  
**Assert**: 200, body `{"status": "ok"}`

---

## test_auth.py

### test_unauthenticated_returns_401
**Fixtures**: client  
**Action**: GET /api/candidates (no header)  
**Assert**: 401, body has `"detail"`

### test_login_valid_returns_token_and_user
**Fixtures**: client, seeded_db  
**Action**: POST /api/auth/login `{"email":"admin@hellio.com","password":"admin123"}`  
**Assert**: 200; body.token is non-empty string; body.user.email == "admin@hellio.com"; body.user.role == "admin"

### test_login_wrong_password_returns_401
**Fixtures**: client, seeded_db  
**Action**: POST /api/auth/login with correct email, wrong password  
**Assert**: 401

### test_login_unknown_email_returns_401
**Fixtures**: client, seeded_db  
**Action**: POST /api/auth/login with unknown email  
**Assert**: 401

### test_auth_me_returns_current_user
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/auth/me  
**Assert**: 200; email == "admin@hellio.com", role == "admin"

### test_auth_me_without_token_returns_401
**Fixtures**: client  
**Action**: GET /api/auth/me (no header)  
**Assert**: 401

---

## test_candidates.py

### test_list_returns_only_active
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/candidates  
**Assert**: 200; all items status=="Active"; length==2; cv_t99 absent

### test_list_excludes_archived
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/candidates  
**Assert**: no item with id=="cv_t99" or status=="Archived"

### test_list_experience_sorted_desc
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/candidates; find cv_t01  
**Assert**: cv_t01.experience[0].startYear==2022, experience[1].startYear==2020

### test_detail_returns_full_profile
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/candidates/cv_t01  
**Assert**: 200; keys present: id, fullName, headline, status, contact, summary, skills, experience, education, certifications, languages, sourceCv; contact has email; sourceCv has fileName/format/path

### test_detail_archived_returns_200
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/candidates/cv_t99  
**Assert**: 200; status=="Archived" (detail endpoint does not filter)

### test_detail_unknown_returns_404
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/candidates/cv_ghost  
**Assert**: 404

### test_list_without_auth_returns_401
**Fixtures**: client  
**Action**: GET /api/candidates (no header)  
**Assert**: 401

---

## test_positions.py

### test_list_returns_only_open
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/positions  
**Assert**: 200; all items status=="Open"; length==2; pos_t03 absent

### test_detail_returns_full_position
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/positions/pos_t01  
**Assert**: 200; keys: id, title, status, hiringManagerEmail, description, sourceDocument; requirements.mustHave is a list

### test_detail_null_requirements
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/positions/pos_t02  
**Assert**: 200; requirements is null or absent

### test_detail_unknown_returns_404
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/positions/pos_ghost  
**Assert**: 404

### test_patch_recruiter_persists
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: PATCH /api/positions/pos_t01 `{"title":"Updated Title"}`; then GET  
**Assert**: PATCH 200 with title=="Updated Title"; GET also returns title=="Updated Title"

### test_patch_viewer_returns_403
**Fixtures**: client, viewer_headers, seeded_db  
**Action**: PATCH /api/positions/pos_t01 with viewer_headers  
**Assert**: 403

### test_patch_unknown_returns_404
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: PATCH /api/positions/pos_ghost  
**Assert**: 404

### test_patch_partial_leaves_other_fields
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: Capture original hiringManagerEmail; PATCH with only `{"status":"Closed"}`  
**Assert**: 200; status=="Closed"; hiringManagerEmail unchanged; title unchanged

---

## test_applications.py

### test_list_returns_all_seeded
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/applications  
**Assert**: 200; length==3; ids app_t01, app_t02, app_t03 present

### test_list_filter_by_candidate
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/applications?candidateId=cv_t01  
**Assert**: 200; all candidateId=="cv_t01"; length==2

### test_list_filter_by_position
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/applications?positionId=pos_t01  
**Assert**: 200; all positionId=="pos_t01"; length==2

### test_list_nonexistent_filter_returns_empty
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/applications?candidateId=cv_ghost  
**Assert**: 200; body==[]

### test_list_null_status_serialised
**Fixtures**: client, auth_headers, seeded_db  
**Action**: GET /api/applications; find app_t02  
**Assert**: app_t02.status is null (not missing)

### test_post_creates_201
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: POST /api/applications `{"candidateId":"cv_t02","positionId":"pos_t02"}`  
**Assert**: 201; body.candidateId=="cv_t02"; body.positionId=="pos_t02"; body.status==null

### test_post_persists
**Fixtures**: client, recruiter_headers, auth_headers, seeded_db  
**Action**: POST then GET /api/applications?candidateId=cv_t02  
**Assert**: GET includes item with positionId=="pos_t02"

### test_post_duplicate_returns_409
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: POST `{"candidateId":"cv_t01","positionId":"pos_t01"}` (app_t01 exists)  
**Assert**: 409

### test_post_unknown_candidate_returns_404
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: POST `{"candidateId":"cv_ghost","positionId":"pos_t01"}`  
**Assert**: 404

### test_post_viewer_returns_403
**Fixtures**: client, viewer_headers, seeded_db  
**Action**: POST with viewer_headers  
**Assert**: 403

### test_delete_returns_204
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: DELETE /api/applications/app_t01  
**Assert**: 204; empty body

### test_delete_persists
**Fixtures**: client, recruiter_headers, auth_headers, seeded_db  
**Action**: DELETE app_t01; then GET /api/applications  
**Assert**: GET list has no item with id=="app_t01"

### test_delete_unknown_returns_404
**Fixtures**: client, recruiter_headers, seeded_db  
**Action**: DELETE /api/applications/app_ghost  
**Assert**: 404

### test_delete_viewer_returns_403
**Fixtures**: client, viewer_headers, seeded_db  
**Action**: DELETE /api/applications/app_t01 with viewer_headers  
**Assert**: 403

---

## Summary

| File | Count |
|---|---|
| test_health.py | 1 |
| test_auth.py | 6 |
| test_candidates.py | 7 |
| test_positions.py | 8 |
| test_applications.py | 13 |
| **Total** | **35** |

All 35 tests are RED when first committed. They turn GREEN commit-by-commit as
routers are added in commits 3–7.

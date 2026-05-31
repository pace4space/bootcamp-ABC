# From Codex to Claude Code: Architecture and UI/UX Improvement Proposals

This is a consulting memo, not an implementation mandate.

The target bar is **interview-ready**: clear, defensible, demo-polished, and test-backed. It is not full production hardening. Do not change current source behavior blindly; each proposal below should be implemented only with tests and an explicit acceptance check.

Priority labels:

- `Now`: helps current Ex2/Ex3 clarity or demo reliability.
- `Next`: should happen while implementing Ex4.
- `Later`: production hardening or larger refactor.

## Functional Proposals

### 1. What Is Already Approved

Codex approves the current direction:

- FastAPI + async SQLAlchemy + Pydantic camelCase schemas.
- `Candidate`, `Position`, and `Application` as normalized core entities.
- The frontend `src/lib/db.ts` seam as the UI's data-access boundary.
- Ex3 staged ingestion pipeline: parsing, heuristics, LLM extraction, validation, persistence, logging.
- Heuristics-before-LLM trust hierarchy.
- Append-only extraction observability tables.
- Ex4 planned SQL-RAG architecture with SQL guard, read-only execution, and trace logging.

### 2. Clarification: Transaction Ownership

**Priority:** `Now`  
**Scope:** Retrospective / cleanup, not Ex4-specific.

Current ingestion style: helpers and orchestrators mostly `flush`, and the endpoint commits once after the pipeline returns.

Current CRUD style: some routers mutate and commit inside the route itself, for example `PATCH /positions`.

This is not a bug, but it is inconsistent. The recommended convention is **request-level transaction ownership**:

- Route/orchestrator code owns `commit`.
- Lower-level helpers/services `flush` and return IDs or entities.
- Multi-step workflows should be committed once after all steps succeed.

The benefit is clearer rollback behavior, easier interview explanation, and easier future extraction into service functions.

### 3. Clarification: Ingestion Failure Observability

**Priority:** `Now`  
**Scope:** Retrospective / Ex3 correctness.

The Ex3 docs say every pipeline invocation produces `raw_documents` and `extraction_runs`. Current code does not fully satisfy that sentence.

What currently happens:

- Validation failures after a successful LLM response are logged.
- Parse failures return `422` before any DB log exists.
- Bedrock failures return `422` before `extraction_runs` exists.

This is not a dev/prod difference. In production, the pipeline uses real Bedrock unless a `bedrock_client` is injected. In automated tests, Bedrock is mocked or injected.

Recommended direction:

- Either update docs to narrow the observability claim, or improve code so parse/Bedrock failures are logged where feasible.
- Keep parse failures as HTTP `422`; optionally add a lightweight `ingest_attempts` table later if "log even unparseable uploads" matters.
- For Bedrock failures after parse succeeds, log `raw_documents` plus a failed `extraction_runs` row with status `failed` and the error message.
- Add tests for Bedrock failure logging.

### 4. Backend Service Boundary

**Priority:** `Now`  
**Scope:** Retrospective and future-friendly.

Keep simple read endpoints in routers. Move multi-step write flows into service/orchestrator functions.

Start with:

- Ingestion workflows.
- Application add/remove.
- Position patch, especially requirements replacement.

Do not introduce a full repository abstraction yet. The current app is not large enough to justify that extra layer.

### 5. API Error Contract

**Priority:** `Next`  
**Scope:** Cross-cutting.

Preserve FastAPI validation behavior for standard request validation `422`.

For app-generated domain errors, add a consistent shape:

```json
{
  "code": "application_duplicate",
  "message": "Application already exists",
  "details": {}
}
```

Frontend code should map these errors to inline error states. Add tests for `401`, `403`, `404`, `409`, and expected app-level `422` responses.

### 6. Auth And Session Behavior

**Priority:** `Now` for demo polish, `Later` for production hardening  
**Scope:** Retrospective / demo polish.

Recommended interview-ready improvements:

- Fail fast outside development if `SECRET_KEY` is still `dev-secret-change-me`.
- Add frontend token rehydration with `/auth/me`.
- Keep the current JWT approach for interview scope.

Treat httpOnly cookies, refresh tokens, and CSRF protection as future production-hardening topics rather than immediate scope.

### 7. Data Loading And Frontend State

**Priority:** `Now`  
**Scope:** Retrospective frontend quality.

Introduce a tiny async resource pattern or hook that standardizes:

- `loading`
- `error`
- `data`
- retry
- abort-on-unmount

Also consolidate duplicated fetch paths, especially `PositionsProvider` versus `PositionsList`. Add mutation pending states plus rollback/error handling for application add/remove.

Do not add TanStack Query unless the app scope grows enough to justify it.

### 8. Ex4+ Functional Guardrails

**Priority:** `Next`  
**Scope:** Ex4 onward.

For SQL-RAG:

- Keep generated SQL untrusted.
- Enforce a deterministic SELECT-only guard.
- Execute with read-only transaction behavior.
- Persist `query_runs`.
- Return trace data to the UI.
- Treat a dedicated read-only DB role as later production hardening.

## UI/UX Proposals

### 1. What Is Already Good

Codex approves:

- Simple route structure.
- Clear candidates / positions / compare mental model.
- Operational UI direction rather than marketing-style UI.
- Useful empty-state presence in list screens.
- Role-gated mutation controls.

### 2. Visual System

**Priority:** `Next`  
**Scope:** Retrospective UI polish.

Recommended direction:

- Define one primary accent color.
- Reserve semantic colors for status only.
- Reduce ad hoc blue / indigo / purple usage.
- Add reusable primitives for buttons, inputs, badges, and panels.
- Keep the visual language quiet, dense, and HR-operations focused.

Avoid landing-page tropes. This app should feel like a precise internal tool.

### 3. Loading, Empty, Error States

**Priority:** `Now`  
**Scope:** Retrospective UX quality.

Replace plain `Loading...` with skeletons shaped like the final layout.

Make empty states more specific:

- Search produced no candidates.
- Position filter produced no candidates.
- Candidate has no applications.
- Position has no linked candidates.

Show inline API and mutation errors consistently. Add retry where appropriate.

### 4. Responsive Layout

**Priority:** `Now`  
**Scope:** Retrospective UI correctness.

Recommended fixes:

- Fix `Compare` mobile layout; use single-column stacking below tablet width.
- Ensure candidate and position headers wrap cleanly.
- Keep action rows usable on mobile.
- Prefer CSS grid with explicit responsive breakpoints.

### 5. Accessibility

**Priority:** `Now`  
**Scope:** Retrospective best practice.

Recommended fixes:

- Replace symbol-only `x`/close controls with text or icon buttons with adequate hit area.
- Add consistent visible focus states.
- Keep form labels above inputs.
- Add helper/error text below inputs.
- Verify color contrast on status badges.
- Ensure keyboard navigation through nav, forms, lists, and mutation actions.

### 6. Product Feel

**Priority:** `Next`  
**Scope:** UI/UX direction.

Recommended direction:

- Avoid landing-page visuals, purple gradients, and decorative hero patterns.
- Favor scannable work queues over large cards.
- Use tables or structured rows where comparison/scanning is the actual workflow.
- Consider a future dashboard only when it summarizes real operational data.

### 7. Ex4 Chat UI

**Priority:** `Next`  
**Scope:** Ex4 onward.

Make `/chat` feel like a traceable work tool, not a generic chatbot.

The UI should show:

- Answer.
- SQL.
- Row count.
- Columns.
- Retrieved rows.
- "No rows found" state.

Use collapsible trace panels. Add loading states for "generating SQL" and "grounding answer" if the backend exposes stages later.

## Priority Map

### Now

- Transaction ownership doc/cleanup.
- Ingestion Bedrock failure logging.
- Async frontend resource pattern.
- Loading/error states.
- Responsive compare fix.
- Auth session rehydration for demo reliability.

### Next

- API error envelope.
- Ex4 query logging and trace UI.
- Chat UX.
- Shared UI primitives.
- Visual system consolidation.

### Later

- Dedicated read-only DB role.
- Generated OpenAPI TypeScript types.
- TanStack Query.
- Refresh-token or cookie auth.
- Pagination for large datasets.
- `ingest_attempts` table if unparseable uploads must be audited.

## Test Notes

### Functional Tests

- Ingestion validation failure logs a failed run.
- Bedrock failure after parse logs a raw document and failed extraction run if implemented.
- Transaction rollback leaves no partial candidate/position child rows.
- Application duplicate returns stable `409`.
- Auth fails fast when production secret is unsafe.
- Ex4 guard rejects DML/multi-statement SQL and appends/caps limits.

### Frontend Tests

- Login error and rehydration behavior.
- Protected route redirect.
- Candidates/positions loading, empty, and error states.
- Application add/remove success and failure.
- Compare page with missing params, not-found candidate, and mobile-friendly rendering.
- Chat answer with trace panel once Ex4 exists.

## Assumptions

- This memo is for Claude Code or another implementation agent.
- The target is interview-ready quality, not full production hardening.
- No source code should be changed as part of creating this memo.
- Recommendations are proposals requiring tests, not automatic truth.
- Retrospective recommendations can be implemented before, during, or after Ex4, but they should not be mixed into Ex4 without explicit test coverage.

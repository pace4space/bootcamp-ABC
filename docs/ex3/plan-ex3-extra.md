# Plan: Ex3-Extra — State Management Refinements

## Problem Statement

Three issues surfaced during architecture review of the Ex2 frontend:

### 1. N+1 fetch in PositionDetail (correctness bug)
`PositionDetail` has a `useEffect` that watches `applications` from context.
Every time any application changes app-wide, it re-fetches *every linked candidate
individually* — N API calls per change. With 10 candidates under a position and
a user actively adding applications elsewhere, this floods the backend.

### 2. Duplicate per-page fetches (efficiency)
Both `CandidatesList` and `CandidateProfile` independently call `getPositions()`
on mount. Navigating between two profiles = 4 position fetches. In Ex1 this was
invisible (JSON). In Ex2 (FastAPI over a real network) it becomes perceptible and
unnecessary.

### 3. No user feedback on mutation errors (UX)
`ApplicationsContext.add` and `remove` await the API but callers never catch
rejections. A server error silently swallows — the user sees nothing happen and
doesn't know to retry.

---

## Solution: Two New Contexts + Error Handling

### CandidatesContext  (`src/context/CandidatesContext.tsx`)
Mirrors the existing `ApplicationsContext` pattern exactly:
- Fetches all candidates once per login (`token` dependency)
- Exposes `{ candidates, loading }`
- All pages read from this cache; no page fetches candidates independently

### PositionsContext  (`src/context/PositionsContext.tsx`)
Same pattern as CandidatesContext for positions:
- Fetches all positions once per login
- Exposes `{ positions, loading }`

### PositionDetail fix
Replace the N+1 async effect with a synchronous `useMemo` over the context arrays:
```ts
const linked = useMemo(() =>
  applications
    .filter(a => a.positionId === id)
    .flatMap(app => {
      const candidate = candidates.find(c => c.id === app.candidateId)
      return candidate ? [{ candidate, app }] : []
    }),
  [id, applications, candidates]
)
```
Zero extra API calls. Derives linked candidates locally.

### Error handling
Add per-page `error` state around `add`/`remove` calls. The context already
propagates exceptions (no silent swallow there); callers just need try/catch.
Errors surface as inline messages near the relevant action.

---

## Files Affected

| File | Change |
|---|---|
| `src/context/CandidatesContext.tsx` | New — global candidates cache |
| `src/context/PositionsContext.tsx` | New — global positions cache |
| `src/main.tsx` | Add two providers (inside AuthProvider, outside App) |
| `src/pages/CandidatesList.tsx` | Remove local fetches; read from contexts |
| `src/pages/CandidateProfile.tsx` | Remove positions fetch; use PositionsContext; add error UI |
| `src/pages/PositionDetail.tsx` | Remove N+1 effect; derive linked via useMemo; add error UI |

`ApplicationsContext.tsx`, `db.ts`, and `types.ts` are unchanged.

---

## Constraints Respected

- No new npm dependencies (pure React Context + hooks)
- `db.ts` signatures unchanged
- `types.ts` unchanged
- Context default values follow existing AuthContext/ApplicationsContext patterns
- `useMemo` dependencies follow React exhaustive-deps rules

# Segment 08 — Frontend (Suggested Candidates / Recommended Positions)

**Depends on:** 07 (endpoints). No backend unit tests; verify via `tsc -b` + `npm run build` + a manual UI pass.

## Purpose

Surface the two suggestion features in the existing detail pages, reusing Tailwind patterns already in the
codebase. Scores render as badges; candidate-view suggestions show the grounded explanation; sections suppress
themselves when there are no matches.

## Public artifacts

### 1. Types (`src/lib/types.ts`, append after the Chat types)
```ts
export type CandidateMatch = {        // position view
  candidateId: string
  fullName: string
  headline: string
  score: number                       // cosine 0..1
}
export type PositionMatch = {         // candidate view
  positionId: string
  title: string
  score: number
  explanation: string
}
```

### 2. Data seam (`src/lib/db.ts`, append after `askChat` at `db.ts:100`, reuse `apiFetch` at `db.ts:9`)
```ts
export async function getCandidateMatches(positionId: string, token: string): Promise<CandidateMatch[]> {
  return (await apiFetch(`/positions/${positionId}/candidate-matches`, token)).json()
}
export async function getPositionMatches(candidateId: string, token: string): Promise<PositionMatch[]> {
  return (await apiFetch(`/candidates/${candidateId}/position-matches`, token)).json()
}
```
Import the new types into the existing `import type { … } from './types'` line at `db.ts:7`.

### 3. Position view (`src/pages/PositionDetail.tsx`)
- Insert a **"Suggested candidates"** `<section>` right after the existing "Linked candidates" section
  (`PositionDetail.tsx:277-302`).
- Fetch in an effect on `id` change via `getCandidateMatches(id, token)`; hold in local state (mirror how the
  page already fetches the position; token comes from the auth context as elsewhere).
- Render each match as a card reusing the linked-candidate markup (`rounded border border-slate-200 bg-white
  px-4 py-3`): a `<Link to={'/candidates/' + m.candidateId}>` with `m.fullName` + `m.headline`, and a score
  badge reusing the skill-badge style (`rounded bg-blue-100 px-2 py-1 text-sm text-blue-700`) showing
  `{Math.round(m.score * 100)}%`.
- Section heading reuses `text-sm font-semibold uppercase tracking-widest text-slate-400`.
- Empty state: `"No strong candidate matches yet."` (threshold suppressed everything or nothing embedded).

### 4. Candidate view (`src/pages/CandidateProfile.tsx`)
- Insert a **"Recommended positions"** `<section>` after the existing "Applications" section
  (`CandidateProfile.tsx:214` onward).
- Fetch via `getPositionMatches(id, token)`.
- Render each match: `<Link to={'/positions/' + m.positionId}>` with `m.title`, a score badge, and the
  `m.explanation` text in the card (`text-sm text-slate-600`).
- **Suppress the entire section** when the list is empty (requirement: show none if none are genuinely relevant)
  — don't render an empty heading.

## Consistency note
The backend already excludes already-linked candidates / already-applied positions, which mirrors the page's
own `availablePositions` exclusion (`CandidateProfile.tsx:46`) and the `linked` derivation
(`PositionDetail.tsx:49`). So suggestions never duplicate what the page already shows as linked/applied.

## Reused utilities / patterns
- `apiFetch` seam — `src/lib/db.ts:9`.
- Card / badge / section-heading Tailwind — `PositionDetail.tsx:278-301`, `CandidateProfile.tsx:124-217`.
- `Link` navigation, `useMemo`/effect fetch patterns already in both pages.

## Tests / verify
- `npx tsc -b` clean; `npm run build` clean (use the Node 22 path from memory: `~/.nvm/versions/node/v22.22.3/bin/npm`).
- Manual: `npm run dev` →
  - open a position → "Suggested candidates" shows up to 3 with score badges, none already linked;
  - open a candidate → "Recommended positions" shows up to 3 with scores + explanations, and **vanishes**
    entirely for a candidate with no relevant positions.
- Capture screenshots into `docs/ex5/demo/` for the submission (mirrors `docs/ex4/demo/`).

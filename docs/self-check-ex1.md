# Validation & Self-Check — Exercise 1

Completed: 2026-05-27

---

## Test Infrastructure

`npm run test` picks up system `node` (v18), which is incompatible with the installed Vitest/Rolldown. Always run tests as:

```bash
/home/ic/.nvm/versions/node/v22.22.3/bin/node node_modules/.bin/vitest run
```

**Result: 4/4 tests pass.**

---

## Q1: Can you explain differences between two profiles side by side?

**Yes.** `/compare?a=cv_001&b=cv_004` shows:

- **Shared skills** (grey chips, count labelled) — what both candidates have in common
- **Only A / Only B** skills (blue / purple chips, candidate's first name as label) — exact skill gaps
- **Experience** in two columns — role, company, years side by side; most recent first
- **Education** and **Certifications** in two columns — rendered only if either side has them

Example: Aarav Hayes vs Abel McKinney. McKinney has 14 skills vs 9. Shared: AWS, Bash, Docker, Git, Python. McKinney adds Ansible, Helm, full Kubernetes, Terraform, Linux, Prometheus. Hayes adds only Jenkins and ECS. A recruiter can form a clear opinion in under 30 seconds.

---

## Q2: Edge Cases

**Very little experience (`cv_001` — Aarav Hayes, 1 role):**
- CandidateProfile: `experience.length > 0` guard renders the section with just one entry. Clean.
- Compare: `ExperienceColumn` handles `length === 0` with "No experience on file." ✓

**Many short roles:**
No candidate in the current dataset has more than 3 roles. The stacked `border-l-2` list has no clipping — more roles would stack and scroll. Worth adding a candidate with 5–6 short roles before Ex2 to stress test.

**Overlapping roles:**
No overlaps exist in the dataset. If they did, the `startYear desc` sort would render them as sequential entries with visually overlapping year numbers — not a crash, but not visually surfaced as meaningful. Flag for Ex3: if LLM extraction produces overlapping dates, the UI won't crash but won't highlight the overlap.

---

## Q3: Adding a new field (e.g. `projects`, `publications`)

**Yes, without reworking the UI.** The pattern is established:

1. Add type to [types.ts](../src/lib/types.ts) (use `?` for optional arrays)
2. Add data to `candidates.json`
3. Add one section block to [CandidateProfile.tsx](../src/pages/CandidateProfile.tsx):
   ```tsx
   {candidate.projects.length > 0 && (
     <section className="space-y-2">
       <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Projects</h2>
       {/* ... */}
     </section>
   )}
   ```
4. Optionally add a column to [Compare.tsx](../src/pages/Compare.tsx) (same `grid-cols-2` pattern)

`db.ts` returns the full `Candidate` object — new fields flow through automatically with no db changes.

---

## Q4: Non-technical HR person without explanation

**Mostly yes — one known exception.**

Clear without explanation:
- Search bar + position filter on the candidates list
- Section headers (Skills, Experience, Education, etc.)
- Green "Active" status badge
- "Add to a position…" dropdown + button
- `AppStatusBadge` values (Waiting / Screening / Offer / Hired / Rejected)
- "Original CV: cv_001.pdf (opens in browser)" link

**Design signal:** The amber badge **"Pending · not saved until Ex2"** is developer-facing. An HR user would not understand "Ex2". Before Ex2 ships a real persistence layer, this should read "Pending · not saved" or "Draft". Accepted as an intentional Ex1 placeholder.

---

## How This Connects Forward

- `certifications` and `languages` are already in the schema and rendered — the "add a new field" question is already answered by the existing code structure.
- `Application` as a join entity (not a field on `Candidate`) maps 1:1 to the Ex2 Postgres join table; Ex6 agent mutations (`add`, `remove`) already have a place to live.
- `db.ts` as the single data seam means every component is written against the `fetch()` interface — only the function bodies change in Ex2, not the callers.
- Experience sorted by `startYear desc` in `getCandidate()` keeps the Compare view stable regardless of JSON insertion order.

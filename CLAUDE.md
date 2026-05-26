# Hellio HR — Exercise 1 (Candidate Profile Viewer & Diff)

First of 8 exercises building an agent-assisted HR system. Ex1 is **UI-only,
JSON-backed**: no database, no auth, **no LLM/agent in the running app**. The
full plan lives in `docs/plan-v2.md` (v1 preserved in `docs/plan-v1.md`).

The 8-exercise arc (every Ex1 decision is lived with through Ex8):
1. Candidate viewer & diff (here) · 2. FastAPI + Postgres backend · 3. LLM
extraction pipeline · 4. Deterministic search/reporting · 5. Embeddings/vector
search · 6. HR agent (Strands, Gmail MCP, human-in-loop) · 7. Templates MCP
server · 8. Managed agent deployment.

## Principles (non-negotiable)
- **Own every line.** If I can't defend a line in an interview, it shouldn't ship.
  Flag non-obvious patterns and explain them before writing.
- **Technician vs Expert:** solve the category, not just the instance.
- **Solve worthwhile things more than one way** to learn the tradeoff.
- **Token-aware model routing:** Haiku = repetitive extraction/scaffold/format;
  Sonnet = module implementation + test design; Opus = planning + doubt only.
- **Verify before declaring done.** Never say a phase or task is complete without
  running the actual check (file exists, test passes, hook fires). Designed ≠ Done.

## Architecture rules
- **Data model is pure and UI-independent.** Types in `src/lib/types.ts`; data in
  `src/data/*.json`. **Never mix UI concerns with data transformation.**
- **All reads go through `src/lib/db.ts`** — async functions over local JSON today;
  in Ex2 only their bodies change to `fetch()` the FastAPI backend. UI never knows
  the source. Do not import JSON directly into components.
- **`public/cvs/` and `public/jobs/` originals are immutable** — copied, never edited.
- Three JSON files mirror three future DB tables: candidates, positions, applications.
  `Application` is a real join entity (M:N + per-link status), not a field.

## Schema discipline
- Don't hard-code assumptions about profile shape. Optional fields are nullable and
  the UI must render gracefully when they're missing.
- Stable ids everywhere (`cv_001`, `job_001`, `skill-1`); sort lists deterministically
  (experience by `startYear` desc) so comparison is trivial.

## Stack conventions
- Vite + React 19 + TypeScript, React Router v7, **Tailwind v4 for styling — no
  separate CSS files**, React built-in state (no Redux). Vitest for the data layer.
- Functional components + hooks. **No new dependency without asking first.**

## Testing
- `src/lib/db.ts` is **test-first**: test doc → failing tests → implementation.
- UI components are not unit-tested in Ex1 (overkill at this stage).

## Workflow
- **Prompts are versioned artifacts in `/prompts/`**, not chat messages. Ex1
  extraction prompts are throwaway (replaced by the real pipeline in Ex3).
- **Commit every working step**; each commit leaves the app demo-able.
- **JOURNAL.md gets one entry per commit** — what changed, why, alternatives, and
  what I'd defend in an interview.

## Operation SKILLability

A learning system that grows from use. You work normally; the system learns automatically.

### What is SKILLability?
A closed-loop system where skills improve from real use, memory synthesizes from learnings,
and routine becomes more automatic over time. Foundation for autonomous learning (Hermes) in Ex5+.

### Principles
- **Explicit**: Every learning opportunity is named and captured
- **Fail forward**: Mistakes generate learnings; errors don't block work
- **Lazy synthesis**: Memory grows fast, but we consolidate strategically (every 5 commits)
- **Resilient**: Skills degrade gracefully; learning has escape hatches
- **Audit trail**: All changes linked to git commits and decisions

### Agentic Commands (Claude invokes these proactively — no prompting needed)
Live in `.claude/commands/`. Claude watches for triggers and acts without being asked.

| Command | Trigger condition |
|---|---|
| `/memory-synthesize` | After every 5th commit, or when MEMORY.md > 20 entries, or when 3+ entries clearly overlap |
| `/skill-new {name}` | When a pattern appears 3+ times in session notes or .skilllog with no skill covering it |

The user can also call either command manually at any time.

### Automatic Hooks (Bash-level, always running)
1. **`session-start.sh`** (PreToolUse): Creates today's session note from template
2. **`post-commit.sh`** (git hook): Logs commit to .skilllog; emits reminder at 5-commit cadence

### Typical Day (you do nothing extra)
```
Morning:  Open editor → session-start.sh auto-creates today's note
Work:     Code. Claude watches session notes + .skilllog for patterns
Commit:   post-commit.sh logs it. At commit 5, Claude runs /memory-synthesize
Notice:   Claude detects repeated manual workaround → runs /skill-new automatically
End Day:  Claude reviews session note → proposes MEMORY.md entries if warranted
```

### Skill Discipline
- Names: kebab-case with intent prefix — `commit-*`, `gen-*`, `review-*`, `verify-*`, `session-*`
- Every skill must have a `## Learnings` section (start empty; auto-populated from errors)
- Don't create a skill until a pattern has appeared 3+ times
- Skills live in `.claude/skills/{name}/SKILL.md`

### Skill Structure
```markdown
---
name: skill-name
description: What and why
---

## Purpose
Problem it solves

## When to Use
When do you use this?

## Instructions
Numbered steps

## Learnings
Auto-populated when errors occur.
Sections: "Known Issue: {condition} {impact} {recovery}"
```

### Memory Synthesis (Every 5 Commits)
- Review MEMORY.md: count entries, look for related ones
- If 3+ entries share a theme: consolidate into 1 synthesis entry
- Mark originals: "Consolidated into [[new-principle]]"
- Keep focused (<25 entries, not unbounded)

### Session Notes (Ephemeral)
- Daily notes auto-created at session start
- Capture learnings as you work
- Strong signals promoted to MEMORY.md (Hook 3 suggests)
- Auto-archived after review (no clutter)

### Audit Trail (JOURNAL.md)
- Auto-populated by Hook 5 (commit message parser)
- Records: skill creation, memory consolidation, structural changes
- Link to related MEMORY.md entries
- Read as: "Why did we make this decision?"

### Path to Hermes (Ex5+)
By Ex3 end, you have: reproducible skill library + failure logs + focused memory + audit trail.
In Ex5, point Hermes at `.claude/skills/` directory. Hermes takes over autonomous improvement.
Data structures map directly; no rework needed. This is the foundation for autonomous learning.

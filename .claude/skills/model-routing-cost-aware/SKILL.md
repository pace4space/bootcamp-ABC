---
name: model-routing-cost-aware
description: Route tasks to Haiku/Sonnet/Opus based on cost and capability
---

## Purpose
Minimize LLM spend without losing capability. Route by task type, not difficulty.

## When to Use
Whenever calling Claude (explicitly in `.claude/settings.json` or internally).

## Routing Rules

### Haiku 4.5 (fastest, cheapest)
- **Cost**: 1x baseline
- **Use for**:
  - Repetitive work (extraction, formatting, scaffolding)
  - Parallelizable subtasks
  - Confirmation/validation (is this change safe?)
  - Session initialization (read files, ask clarifying questions)

### Sonnet 4.6 (balanced)
- **Cost**: ~2x Haiku
- **Use for**:
  - Implementation (write code, tests, refactors)
  - Module-level design (pick between 2-3 approaches)
  - Code review (identify real bugs, not style)
  - Complex merges

### Opus 4.7 (most capable)
- **Cost**: ~3-4x Haiku
- **Use for**:
  - Planning (architecture, big decisions, uncertainty)
  - Genuine doubt (could go wrong; want the smartest model)
  - Cross-cutting decisions affecting many modules
  - Rare (1-2 per session max)

## Learnings

### Why This Works
- Token count is the limiting factor (Opus costs more because context is longer)
- Most tasks don't need full Opus thinking; Sonnet handles 80% of real work
- Haiku handles 70% of time (setup, validation, repetitive formatting)
- Result: Opus reserved for decisions that genuinely matter

### Session Tracking
- Count model uses per session (Haiku N, Sonnet M, Opus K)
- If Sonnet > 70%, likely over-scoping; consider if Haiku can validate first
- If Opus > 3, likely over-planning; trust local expertise more

## Related
- [[feedback_model-routing-cost]] in MEMORY.md
- CLAUDE.md → "Principles" section (token-aware model routing)

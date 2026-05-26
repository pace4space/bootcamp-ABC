# Path A: Claude Code + Hermes-Style Memory & Skills

**Timeline**: Implement by end of Ex2  
**Effort**: ~2 hours initial setup, ~10 min/session ongoing  
**Goal**: Add memory synthesis + skill learnings without leaving Claude Code

---

## 1. Directory Structure (Create Now)

```
.claude/
├── CLAUDE.md                    (already exists, update below)
├── PATH-A-IMPLEMENTATION.md     (this file)
├── settings.local.json          (already exists)
├── skills/                      (create)
│   ├── commit-correct-attribution/
│   │   └── SKILL.md
│   └── model-routing-cost-aware/
│       └── SKILL.md
└── session-notes/               (create)
    └── TEMPLATE.md
```

---

## 2. Update CLAUDE.md

Add these sections to `/home/ic/bootcamp/ABC/CLAUDE.md`:

```markdown
## Skill Discipline

Skills live in `.claude/skills/{name}/SKILL.md` and can improve over time:

- **Structure**: Each skill has name, description (frontmatter), instructions, and learnings
- **Naming**: Kebab-case with prefixes: `commit-*`, `gen-*`, `review-*`, `model-routing-*`
- **Learnings section**: Document what worked/failed during use
- **Trigger**: When you repeat a pattern 3+ times, formalize as a skill

### Example: `commit-correct-attribution`
```yaml
---
name: commit-correct-attribution
description: Create commits with accurate author attribution, no placeholder trailers
---

## Purpose
Ensure every commit properly cites co-authors. Replaces hardcoded Haiku placeholder.

## Instruction Set
[... detailed steps ...]

## Learnings
- Initially hardcoded `Co-Authored-By: Claude Haiku 4.5` → Wrong
- Feedback: model must be detected or asked, never hardcoded
- Current: check .claude/settings.json model, prompt if ambiguous
- Result: all subsequent commits have correct attribution
```

---

## Memory Synthesis

Keep `MEMORY.md` focused by periodically consolidating:

- **Sync point**: Every 5 commits (pin to JOURNAL.md)
- **Mechanism**: Review MEMORY.md, merge 3+ related entries into 1-2 principles
- **Output**: Update description field in memory file; mark old entry as "consolidated into X"

### Example: Consolidate feedback memories
**Before** (3 related entries):
- feedback_commit-attribution.md
- feedback_model-routing-cost.md
- feedback_architecture-purity.md

**After** (1 synthesis entry):
- feedback_implementation-discipline.md
```markdown
---
name: implementation-discipline
description: Three interlocking practices ensure defendable code
---

## Principles

### 1. Accurate Attribution
Commits cite actual co-authors, never hardcoded placeholders.

### 2. Cost-aware Model Routing
- Haiku: repetitive work (extraction, formatting, scaffolding)
- Sonnet: implementation + testing
- Opus: planning or genuine doubt
Why: LLM cost scales with context; route by task, not difficulty.

### 3. Architecture Purity
Data model is pure; UI never imports JSON directly.
Why: simplifies future migrations (Ex2 adds FastAPI without UI changes).

## Consolidated From
- [[feedback_commit-attribution]]
- [[feedback_model-routing-cost]]
- [[feedback_architecture-purity]] (hypothetical)
```

---

## Session Notes (Ephemeral, discarded after synthesis)

Create one file per day in `.claude/session-notes/`:

### `.claude/session-notes/TEMPLATE.md`
```markdown
# Session: YYYY-MM-DD HH:MM–HH:MM

## What I did
- [X] Implemented feature X
- [X] Fixed bug Y
- [ ] Attempted Z (blocked by W)

## Key Learnings
- Insight 1 (relevant to future sessions)
- Insight 2 (validates or contradicts prior assumption)

## For Next Session
- If pattern X holds, create skill `X-name`
- Remember: constraint Y still applies
- Related memory: [[feedback_model-routing-cost]]

## Blockers
- None / Blocked by W (expected resolution date)
```

### Lifecycle
- **During session**: Update as you go
- **End of session**: 5-min review, save
- **Next session start**: Read if relevant, then delete (archive if noteworthy)
- **Sync point**: If insight appears in 2+ sessions, formalize as MEMORY.md entry

---

## 3. Implement Skills

### Create `.claude/skills/commit-correct-attribution/SKILL.md`

```markdown
---
name: commit-correct-attribution
description: Create commits with accurate author attribution (no placeholder trailers)
---

## Purpose
Every commit must cite the actual co-author(s) who contributed. Do not hardcode model names.

## When to Use
When you run `git commit` and need to add a co-author line.

## Instructions

1. **Determine the actual co-author**
   - Check `.claude/settings.json` for the model used this session
   - Example: `"model": "claude-sonnet-4-6"` → co-author is Sonnet 4.6, not Haiku
   - If unclear (mixed models), prompt the user: "Which model contributed most?"

2. **Format correctly**
   ```
   git commit -m "message

   Co-Authored-By: Claude {Model Version} <noreply@anthropic.com>"
   ```
   - Use actual model name (Opus 4.7, Sonnet 4.6, Haiku 4.5)
   - Use commit date convention: `YYYY-MM-DD` if needed, or check git config

3. **Verify before pushing**
   - `git log -1 --pretty=fuller` to confirm attribution
   - If wrong, create a NEW commit (never amend, as per project feedback)

## Learnings

### Session 0 (mistake)
- Hardcoded: `Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>`
- Issue: misleading when Sonnet was actually used
- Feedback: "drop hardcoded trailer; actual model must be detected"

### Session 1+ (improvement)
- Now reads .claude/settings.json for model
- Falls back to prompt if ambiguous
- Verified: all commits post-fix have correct attribution
- Result: git blame is now accurate

## Related
- [[feedback_commit-attribution]] in MEMORY.md
- CLAUDE.md → "Commit Attribution" section
```

### Create `.claude/skills/model-routing-cost-aware/SKILL.md`

```markdown
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
  - Cross-cutting decisions that affect many modules
  - Rare (1-2 per session max)

## Learnings

### Why this works
- Token count is the limiting factor (Opus costs more because context is longer)
- Most tasks don't need full Opus thinking; Sonnet handles 80% of real work
- Haiku handles 70% of time (setup, validation, repetitive formatting)
- Result: Opus reserved for decisions that genuinely matter

### Session tracking
- Count model uses per session (Haiku N, Sonnet M, Opus K)
- If Sonnet > 70%, likely over-scoping; consider if Haiku can validate first
- If Opus > 3, likely over-planning; trust local expertise more

## Related
- [[feedback_model-routing-cost]] in MEMORY.md
- CLAUDE.md → "Principles" section (token-aware model routing)
```

---

## 4. Set Up Session Notes

### Create `.claude/session-notes/TEMPLATE.md` (template, don't track)
Just the template above.

### Create first session note: `.claude/session-notes/2026-05-26.md`
```markdown
# Session: 2026-05-26 14:00–14:45

## What I did
- [X] Read claude-code-guide patterns
- [X] Analyzed Hermes Harness documentation
- [X] Created ASSESSMENT.md and PATH-A-IMPLEMENTATION.md

## Key Learnings
- Claude Code + Hermes are complementary, not competing
- Hermes excels at autonomous skill improvement; Claude Code at IDE integration
- Can adopt Hermes patterns (memory synthesis, skill learnings) in Claude Code without major changes

## For Next Session
- Implement the two skills (commit-correct-attribution, model-routing-cost-aware)
- Add "Skill Discipline" section to CLAUDE.md
- Test skill usage in Ex2 when you add FastAPI

## Blockers
- None

## Related Decisions
- Chose Path A over Path B or C (immediate practicality)
- Will revisit Path B in Ex5 when LLM extraction patterns stabilize
```

---

## 5. Memory Sync Process

**When to consolidate** (pin to JOURNAL.md at commit time):

```markdown
# JOURNAL.md

## Commit: [hash] Add commit-correct-attribution skill (2026-05-26)

What changed:
- Created `.claude/skills/commit-correct-attribution/SKILL.md`
- Formalizes feedback_commit-attribution memory
- Updates git workflow to never hardcode co-author

Why:
- Mistake: hardcoded Haiku trailer was misleading
- Learning: automation should read actual model from .claude/settings.json
- This skill embeds the correction for future sessions

Learnings:
- Session notes + skills are better than memory for "how-tos"
- Memory should stay at principle level (why), skills at tactic level (how)

**Memory sync**: All feedback about attribution/accuracy consolidated into skills + CLAUDE.md section. Original [[feedback_commit-attribution]] can be marked "superseded by commit-correct-attribution skill".
```

---

## 6. Workflow Integration

### At start of each session
1. Open `.claude/session-notes/TEMPLATE.md`
2. Copy to `.claude/session-notes/YYYY-MM-DD.md`
3. Skim if you've created session notes before (see what you noted yesterday)
4. Keep it open in a split pane

### During session
1. Update session notes as you discover learnings
2. When you complete a task, note it
3. When you hit a blocker or validate an assumption, note it

### At end of session
1. Review session notes (5 min)
2. Identify any learnings that are strong signals (appeared in 2+ sessions or contradicted prior assumption)
3. If strong signal: create or update MEMORY.md entry
4. Delete session notes file (archive if noteworthy)

### Sync point (every 5 commits, pin to JOURNAL.md)
1. Review MEMORY.md for related entries
2. If 3+ entries share a theme, create a synthesis entry
3. Mark originals as "consolidated into X"
4. Update CLAUDE.md if principle changes

---

## 7. Example Workflow (Ex2)

**Commit 1**: Add FastAPI endpoint  
→ Session note: "FastAPI naming convention different from React; might create skill later"

**Commit 2**: Add database query  
→ Session note: "Sonnet implementation was fast, no Opus needed; Haiku could've done validation"

**Commit 3**: Add test  
→ Session note: "Same FastAPI pattern as Commit 1; maybe time to create skill"

**Commit 4**: Refactor shared FastAPI helper  
→ Session note: "Refactor validated the pattern. Pattern is stable enough for skill."

**Commit 5**: Document FastAPI setup  
→ **SYNC POINT**  
  - Memory review: feedback_model-routing-cost already covers this
  - Create `.claude/skills/fastapi-crud-pattern/SKILL.md` (formalizes Commits 1-4)
  - Note in JOURNAL.md: "Observed pattern stabilizes by commit 4; skill created by commit 5"

---

## 8. Files to Create Right Now

```bash
# In /home/ic/bootcamp/ABC/.claude/

mkdir -p skills/commit-correct-attribution
mkdir -p skills/model-routing-cost-aware
mkdir -p session-notes

# Copy SKILL.md files from sections above
# Create TEMPLATE.md from template section
# Create first session note (2026-05-26.md)
```

---

## 9. Checklist

### This Week (implement)
- [ ] Create `.claude/skills/commit-correct-attribution/SKILL.md`
- [ ] Create `.claude/skills/model-routing-cost-aware/SKILL.md`
- [ ] Create `.claude/session-notes/` directory + TEMPLATE.md
- [ ] Update CLAUDE.md with "Skill Discipline" + "Memory Synthesis" sections
- [ ] Create first session note (2026-05-26.md)
- [ ] Update JOURNAL.md with memory sync note

### Ongoing (every session)
- [ ] Create daily session note
- [ ] Update as you discover learnings
- [ ] Review at end of session (5 min)
- [ ] Delete after consolidation or archival

### Every 5 commits (sync point)
- [ ] Review MEMORY.md for related entries
- [ ] Consolidate 3+ related entries if present
- [ ] Create skill if pattern is stable (3+ instances)
- [ ] Update CLAUDE.md if principle changes
- [ ] Note in JOURNAL.md

---

## 10. Success Criteria

✅ Skills are explicit, versionable, and linked to feedback  
✅ MEMORY.md stays focused (<30 entries) via periodic synthesis  
✅ Session notes capture learnings without clutter  
✅ By Ex2 end: 2-3 skills + consolidated memory synthesis  
✅ All skills have "Learnings" section with concrete examples  
✅ CLAUDE.md can cite `.claude/skills/` for "how" details  

---

## 11. Transition to Path B (Future, Ex5+)

If you want to add Hermes later:
- `.claude/skills/*/SKILL.md` format maps to Hermes skill format (almost identical)
- Session notes can be bulk-imported to Hermes memory
- MEMORY.md entries become Hermes user/project memories
- No rework; just point Hermes at your existing structure

---

## Next Steps

1. Create the two skills (commit & model routing) **this session**
2. Update CLAUDE.md **this session**
3. Start using session notes in **Ex2**
4. Run first memory synthesis at **Ex2 commit 5** (time it)
5. Evaluate if this rhythm works; adjust in Ex3

That's it. No new tools, no dependencies, no breaking changes.

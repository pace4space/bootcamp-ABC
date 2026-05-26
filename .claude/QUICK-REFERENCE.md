# Claude Code + Hermes: Quick Reference Card

**Print or pin to your desk.**

---

## 1. Three Integration Paths

| Path | Timeline | Effort | Keep IDE? | Key Win |
|------|----------|--------|-----------|---------|
| **A: Enhance Claude Code** | Start Ex2 | 2 hrs + 10 min/session | ✅ Yes | Memory synthesis + skill learnings (you control when) |
| **B: Parallel Hermes** | Consider Ex5 | 4-6 hrs + 10 min/day | ✅ Yes | Autonomous skill improvement + cross-session recall |
| **C: Full migration** | Future (not for ABC) | High | ❌ CLI only | Full autonomy, multi-platform, but lose IDE |

**Recommendation**: Start Path A (low risk, high signal). Evaluate Path B in Ex5 if LLM extraction patterns repeat.

---

## 2. Path A: Immediate Actions (Do This Week)

### Create two skills
```bash
mkdir -p .claude/skills/commit-correct-attribution
mkdir -p .claude/skills/model-routing-cost-aware
# Add SKILL.md files (templates in PATH-A-IMPLEMENTATION.md)
```

### Update CLAUDE.md
Add two sections:
- "Skill Discipline" (skills live in `.claude/skills/`, have Learnings section)
- "Memory Synthesis" (consolidate 3+ related entries into 1 principle every 5 commits)

### Set up session notes
```bash
mkdir -p .claude/session-notes
# Create TEMPLATE.md + first daily note (2026-05-26.md)
```

**Result**: Formalized two existing feedback entries + infrastructure for capturing future learnings.

---

## 3. Daily Workflow (Path A)

### At start
```
1. Create .claude/session-notes/YYYY-MM-DD.md from TEMPLATE
2. Skim yesterday's notes (if relevant)
3. Keep notes open in split pane
```

### During work
```
- Update session notes as you discover learnings
- When pattern repeats 3+ times, note "might create skill"
```

### At end (5 min)
```
1. Review session notes
2. If strong signal (2+ sessions or contradicts assumption): save as MEMORY.md
3. Delete session note (archive if noteworthy)
```

### Every 5 commits (sync point, pin to JOURNAL.md)
```
1. Review MEMORY.md — are 3+ entries related?
2. If yes: create synthesis entry (merge into 1 principle)
3. Create skill if pattern is stable (3+ instances)
4. Update CLAUDE.md if principle changes
```

---

## 4. Skill Template (Minimal)

```markdown
---
name: skill-name
description: One-line what and why
---

## Purpose
What problem does this solve?

## Instructions
[Detailed steps]

## Learnings
### Initial (mistake)
- What was wrong?
- Why did it fail?
- What was the feedback?

### Improvement (current)
- What changed?
- Why does this work?
- How do we know?
```

---

## 5. When to Formalize a Skill

- **3+ instances**: You've done the same thing 3+ times. Create a skill.
- **Repeated feedback**: Same correction appears in 2+ sessions. Make it a skill.
- **Stable pattern**: The approach worked consistently. Lock it down.

**Don't wait for perfection.** Skills improve with use (via the Learnings section).

---

## 6. Memory Synthesis Template

```markdown
---
name: principle-name
description: Short summary of consolidated entries
---

## Rule
State the principle or pattern clearly.

## Why
What problem does this solve? What feedback drove it?

## How to Apply
When/where does this kick in? What's the decision?

## Consolidated From
- [[memory_entry_1]]
- [[memory_entry_2]]
```

---

## 7. When to Synthesize Memory

**Every 5 commits**, review MEMORY.md:
- Count entries: if >25, time to consolidate
- Look for themes: 3+ entries about similar topic?
- Check dates: are 2+ from same session/week (likely same insight)?

**If any match**: Merge into 1-2 synthesis entries.

---

## 8. File Structure

```
.claude/
├── CLAUDE.md (add Skill Discipline + Memory Synthesis sections)
├── PATH-A-IMPLEMENTATION.md (detailed guide)
├── QUICK-REFERENCE.md (this file)
├── settings.local.json (already exists)
├── skills/
│   ├── commit-correct-attribution/SKILL.md
│   ├── model-routing-cost-aware/SKILL.md
│   └── [future-skill]/SKILL.md
└── session-notes/
    ├── TEMPLATE.md
    ├── 2026-05-26.md (first daily note)
    └── [YYYY-MM-DD].md (daily notes, deleted after consolidation)

MEMORY.md (home directory)
├── project_claude-code-hermes-integration (this initiative)
├── feedback_commit-attribution
├── feedback_model-routing-cost
├── [future-synthesis entries]
```

---

## 9. Hermes Integration (Future, Path B)

**If you adopt Hermes in Ex5+:**
- `.claude/skills/` format maps directly to Hermes skill format
- Session notes can bulk-import to Hermes memory
- MEMORY.md entries become Hermes user/project memories
- No rework—just point Hermes at existing structure

---

## 10. Success Metrics (By Ex2 end)

✅ 2 skills with Learnings sections  
✅ CLAUDE.md updated with Skill Discipline + Memory Synthesis  
✅ Daily session notes for 1+ week  
✅ First memory synthesis by commit 5  
✅ All feedback memories linked to skills or principles  

---

## 11. FAQ

**Q: Isn't this extra work?**  
A: Setup takes 2 hours. Ongoing is 10 min/session (you're already thinking about learnings; this just captures them). Memory synthesis (5 min) happens every 5 commits, not daily.

**Q: What if I don't use session notes?**  
A: Path A still works. Skills + memory synthesis are the core. Session notes are the mechanism to surface learnings; you can skip them if you prefer JOURNAL.md entries instead.

**Q: When do I move to Path B (Hermes)?**  
A: When you notice: (a) repeating extraction failures in Ex3-4, (b) skills improving faster than manual updates, (c) want async batch learning. Likely Ex5+.

**Q: Can I use Hermes now (Path B) instead of Path A?**  
A: Hermes is standalone. Path A is Claude Code only. They're complementary. If you have time and want to learn Hermes, go ahead—but Path A is lower risk for your timeline.

**Q: Do I have to pick one path?**  
A: No. Start Path A. If in Ex5 you want autonomous skill improvement, layer Path B on top. No rework.

---

## 12. Decision: I Choose Path A

**Because:**
- ✅ Low effort (2 hours + 10 min/session)
- ✅ No new dependencies
- ✅ Works with existing Claude Code IDE integration
- ✅ Formalizes existing feedback (commit attribution, model routing)
- ✅ Foundation for Path B later if needed

**Timeline:**
- This week (Ex1): Create skills + update CLAUDE.md
- Ex2: Use daily session notes, run first memory synthesis
- Ex5: Evaluate if autonomous learning (Path B) would help

---

**Files to read:**
- `/home/ic/bootcamp/ABC/ASSESSMENT.md` — full analysis
- `/home/ic/bootcamp/ABC/.claude/PATH-A-IMPLEMENTATION.md` — step-by-step

**Questions?**  
See ASSESSMENT.md sections 1-4 or contact me.

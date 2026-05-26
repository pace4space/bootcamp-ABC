# Claude Code vs Hermes Harness: Visual Integration Map

## Current State (Ex1)

```
┌─────────────────────────────────────────┐
│         VS Code IDE Extension           │
│  (Claude Code - current setup)          │
├─────────────────────────────────────────┤
│                                         │
│  Memory: MEMORY.md                      │
│  ├── feedback_commit-attribution        │
│  └── feedback_model-routing-cost        │
│                                         │
│  Skills: .claude/skills/ (static docs)  │
│  └── [none yet - formalizing]           │
│                                         │
│  Hooks: .claude/hooks/ (security)       │
│  └── warn-env.sh, block-dangerous...    │
│                                         │
│  CLAUDE.md: Principles + Architecture   │
│  └── (excellent, no changes needed)     │
│                                         │
└─────────────────────────────────────────┘

Current capability: Task execution + memory recall
Limitation: No memory synthesis, skills don't improve
```

---

## Path A: Enhance Claude Code (Recommended Ex2+)

```
┌──────────────────────────────────────────────┐
│       VS Code IDE Extension                  │
│    (Claude Code - enhanced)                  │
├──────────────────────────────────────────────┤
│                                              │
│  Memory: MEMORY.md                           │
│  ├── feedback_commit-attribution             │
│  ├── feedback_model-routing-cost             │
│  ├── project_claude-code-hermes-integration  │
│  └── [synthesis entries, e.g.                │
│      implementation-discipline]              │
│                                              │
│  Skills: .claude/skills/ (with learnings)   │
│  ├── commit-correct-attribution/SKILL.md     │
│  │   ├── Purpose                             │
│  │   ├── Instructions                        │
│  │   └── ✨ Learnings section                │
│  ├── model-routing-cost-aware/SKILL.md       │
│  │   └── ✨ Learnings section                │
│  └── [future skills as patterns stabilize]   │
│                                              │
│  Session Notes: .claude/session-notes/       │
│  ├── TEMPLATE.md                             │
│  ├── 2026-05-26.md (daily, ephemeral)        │
│  └── [captured learnings before delete]      │
│                                              │
│  CLAUDE.md: Enhanced with Discipline         │
│  ├── Skill Discipline (structure, naming)    │
│  ├── Memory Synthesis (consolidation rules)  │
│  └── Session Notes (ephemeral learnings)     │
│                                              │
│  JOURNAL.md: Sync Points                     │
│  └── Every 5 commits: Memory synthesis       │
│      + Skill creation as patterns stabilize  │
│                                              │
└──────────────────────────────────────────────┘

Capability: Task execution + memory synthesis + skill learnings
Effort: 2 hours setup + 10 min/session
Gain: Formalized feedback → reusable skills
Reversible: Yes (just markdown files)
```

---

## Path B: Add Hermes (Parallel, Consider Ex5+)

```
┌──────────────────────────────────────────────┐
│   VS Code (Claude Code - unchanged)          │
│   + Background CLI/Messaging (Hermes)        │
├──────────────────────────────────────────────┤
│                                              │
│  Claude Code (IDE):                          │
│  ├── .claude/skills/ (shared with Hermes)    │
│  ├── MEMORY.md (manual entries)              │
│  └── Session notes (your daily driver)       │
│                                              │
│  ⟷ Shared: .claude/skills/ directory        │
│  │ (Hermes improves, Claude Code uses)      │
│  │                                          │
│  Hermes (Background Agent):                  │
│  ├── Autonomous skill improvement ✨        │
│  ├── FTS5 memory + LLM summarization ✨      │
│  ├── Honcho user modeling ✨                 │
│  ├── Cross-session recall ✨                 │
│  ├── Slack/Discord/voice integration ✨     │
│  └── Batch operations (async learning)       │
│                                              │
│  Workflow:                                   │
│  • You code in IDE (Claude Code)             │
│  • Hermes runs overnight (batch synthesis)   │
│  • Next morning: improved skills ready       │
│  • You use skills in IDE; Hermes logs use    │
│  • Cycle repeats (feedback loop)             │
│                                              │
└──────────────────────────────────────────────┘

Capability: Everything from Path A + autonomous learning
Effort: 4-6 hours setup + 10 min/day Hermes batch
Gain: Skills improve without manual intervention
Tradeoff: Two systems, two mental models
```

---

## Hermes Closed Learning Loop (What You Gain in Path B)

```
 ┌──────────────────────────────────────────────┐
 │                                              │
 │  1. You use Claude Code / run Hermes batch   │
 │     │                                        │
 │     ├─→ Extract Learnings                    │
 │     │   (repeated patterns, failures)        │
 │     │                                        │
 │     ├─→ 2. Agent-curated Memory              │
 │     │       (nudge: summarize, consolidate?) │
 │     │                                        │
 │     ├─→ 3. Autonomous Skill Creation         │
 │     │       (5+ instances → create skill)    │
 │     │                                        │
 │     ├─→ 4. Skill Self-Improvement            │
 │     │       (RL-style: refine based on use)  │
 │     │                                        │
 │     ├─→ 5. Cross-Session Recall              │
 │     │       (FTS5 search + LLM summarize)    │
 │     │                                        │
 │     └─→ 6. User Modeling                     │
 │           (Honcho: learns your preferences)  │
 │                                              │
 │  7. Next session: Agent knows more           │
 │     (skills improved, memory synthesized)    │
 │                                              │
 └──────────────────────────────────────────────┘

  🔄 Feedback Loop: Your actions → Agent learning → Better agent
```

---

## Timeline & Decisions

```
                        Ex1           Ex2           Ex3           Ex5-6
                        │             │             │             │
    Current             │             │             │             │
    Claude Code ────────┼─────────────┼─────────────┼─────────────┼───
                        │             │             │             │
                        │      PATH A │             │             │
    + Memory Synthesis  │      (2-hr  │             │             │
    + Skills with       │      setup) │             │             │
    Learnings section   │             │             │             │
                        │      ✓ Impl │ ✓ Using     │             │
                        │             │             │             │
                        │             │             │      PATH B │
                        │             │             │      Parallel
                        │             │             │      Hermes? 
                        │             │             │      (eval) ✓
                        │             │             │             │

Decision Points:
 • Now (Ex1):      Choose Path A (low risk, low effort)
 • Ex2 Commit 5:   First memory synthesis—does it work?
 • Ex3-4:          Extraction failures generating learnings?
 • Ex5:            Patterns stabilizing? Consider Path B?
 • Ex8:            Deploy which agent (Claude Code or Hermes)?
```

---

## Why Claude Code + Hermes are Complementary

```
                Claude Code          Hermes
                ─────────────────────────────
IDE Integration     ✅ Best-in-class     ❌ CLI/messaging
Memory              Explicit/Manual       Auto-curated ✅
Skills              Static docs           Improving ✅
User Modeling       Manual                Automatic ✅
Cross-session       Manual recall         FTS5 + LLM ✅
Permission Model    Tool allowlist        Command approval
Background Work     No                    Yes ✅
Multi-platform      No                    Yes (Slack/voice) ✅

Conclusion:
• Use Claude Code when: You're actively coding in IDE
• Use Hermes when: You want async learning, multi-platform, or autonomous skills
• Use Both when: You want IDE + autonomous background agent

Path A = Get some Hermes benefits without leaving Claude Code
Path B = Full Hermes capabilities while keeping IDE integration
```

---

## Example: Extraction Failure → Skill Improvement (Ex3)

```
Path A (Manual):
 • You try LLM extraction 3 times
 • Each fails differently
 • You note learnings in session notes
 • After 3 sessions, you consolidate into MEMORY.md
 • Later (maybe never), you formalize as a skill
 • Skill improvements are manual

Path B (Autonomous):
 • You try LLM extraction 3 times (Hermes logs each)
 • Hermes notices pattern: "extraction failing on X"
 • Hermes autonomously creates skill: `extract-field-X`
 • You use skill in IDE
 • Hermes logs success/failure, refines instructions
 • Next session: skill is better (you don't do anything)
 • Cycle repeats (feedback loop)
```

---

## Decision Tree

```
                    Start here
                        │
                        ▼
          Do you want autonomous
          skill improvement?
                │           │
            No  │           │  Yes
                │           │
            ┌───▼──┐    ┌───▼────────┐
            │Path A │    │Path B later?│
            │(Now)  │    │(Ex5+)       │
            └───┬──┘    └────┬────────┘
                │            │
            Implement:    When patterns
            • Skills      stabilize in
            • Memory      extraction
              synthesis   pipeline
            • Session
              notes

                └─────────┬──────────┘
                          │
                      Install Hermes
                      Point to existing
                      .claude/skills/
                      Import MEMORY.md
```

---

## What to Read Next

1. **QUICK-REFERENCE.md** (2 min) — One-page summary, do-this-week actions
2. **PATH-A-IMPLEMENTATION.md** (20 min) — Step-by-step guide for Path A
3. **ASSESSMENT.md** (40 min) — Deep analysis of both paths, tradeoffs
4. **Hermes docs** (if interested) — https://hermes-agent.nousresearch.com/docs

---

## Checklist: Path A (Do This Week)

- [ ] Read QUICK-REFERENCE.md (2 min)
- [ ] Create `.claude/skills/commit-correct-attribution/SKILL.md`
- [ ] Create `.claude/skills/model-routing-cost-aware/SKILL.md`
- [ ] Update CLAUDE.md with "Skill Discipline" + "Memory Synthesis" sections
- [ ] Create `.claude/session-notes/TEMPLATE.md`
- [ ] Create first session note (`.claude/session-notes/2026-05-26.md`)
- [ ] Test in Ex2: use session notes for 1 week
- [ ] Run first memory synthesis at commit 5 (pin to JOURNAL.md)
- [ ] Decide: continue Path A in Ex3, or prepare for Path B?

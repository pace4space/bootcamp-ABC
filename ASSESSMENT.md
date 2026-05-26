# Claude Code vs Hermes Harness: Integration Assessment

**Date**: 2026-05-26 | **Context**: ABC HR bootcamp exercise series (Ex1-8)

---

## Executive Summary

**Claude Code** is your current IDE-integrated assistant with static skills/hooks and explicit memory. **Hermes Harness** is an autonomous background agent that learns, evolves, and refines skills over time via closed feedback loops.

**Key finding**: You can **incrementally adopt Hermes patterns into Claude Code** without ripping out your current setup. This assessment shows what to layer in and why.

---

## 1. Claude Code: Current State

### What You Have
- **Embedded in VS Code**: works seamlessly within editor
- **Static skills** (`.claude/skills/`): reusable commands, no self-improvement
- **Static hooks** (`.claude/hooks/`): security gates, logging
- **Project-scoped CLAUDE.md**: defines your principles (owns every line, technician vs expert, token routing)
- **Explicit memory system** (newer): `.claude/projects/-home-ic-bootcamp-ABC/memory/` with typed memories (user, feedback, project, reference)
- **No autonomous learning loop**: memory doesn't auto-refine, skills don't improve during use

### Strengths
✅ Tight IDE integration (point-and-click file navigation)  
✅ Permission model is explicit (you approve each tool call)  
✅ Memory is structured with frontmatter (findable, versionable)  
✅ Already has CLAUDE.md discipline for this project  
✅ Can apply Haiku/Sonnet/Opus routing within one session  

### Gaps (Hermes advantage)
❌ Skills are static documents—no self-improvement from use  
❌ No autonomous nudge system (memory needs manual review)  
❌ No cross-session skill synthesis (each session restarts)  
❌ Memory grows unbounded (no summarization/compression)  
❌ No user modeling beyond explicit memory entries  

---

## 2. Hermes Harness: Key Innovations

### The Closed Learning Loop
Hermes uniquely combines four mechanisms:

1. **Agent-curated memory with periodic nudges**
   - Agent reviews its own memory, flags stale entries, suggests consolidation
   - Reduces noise, keeps memory high-signal
   - Roughly: "I've written 15 design decisions. Let me summarize into 3 principles."

2. **Autonomous skill creation & improvement**
   - When you repeat a task, Hermes creates a skill
   - When you use a skill, it analyzes outcomes and refines it (RL-style)
   - Skills are portable (agentskills.io standard)
   - Example: You solve "commit with correct attribution" 5 times, Hermes proposes `commit-correct-attribution` skill; future uses improve its instructions

3. **FTS5 cross-session recall with LLM summarization**
   - Full-text search over past sessions (SQLite FTS5)
   - When starting new session, agent summarizes relevant prior context
   - Not just "here's your memory file"—Hermes synthesizes what matters for *this* session

4. **Honcho dialectic user modeling**
   - Learns your preferences incrementally (e.g., "prefers terse responses", "wants cost-aware model routing")
   - Refines understanding across sessions
   - Feeds into personality/SOUL.md generation

### Architectural Independence
- **Runs autonomous in background**: not IDE-bound, persists across tool switches
- **Can be CLI-only** or integrated with messaging (Slack, Telegram, Discord, Teams)
- **Trades** tight IDE integration for persistent, evolving agent personality

---

## 3. Integration Strategy: Layers

You have **three integration paths** (not mutually exclusive):

### Path A: Enhance Claude Code with Hermes patterns (Recommended first step)
**Keep Claude Code as primary IDE assistant. Layer in Hermes-style memory & skill discipline.**

**What to implement in Claude Code:**
1. **Memory summarization in CLAUDE.md**
   - Add a "Synthesis" section that distills 5+ related memories into 1-2 principles
   - Example: Your feedback about model routing + cost could become:
     ```markdown
     # Synthesis: Token-aware model routing
     - Haiku for repetitive work (extraction, formatting, scaffolding)
     - Sonnet for implementation + testing
     - Opus only for planning or genuine doubt
     Why: LLM cost scales with context window; route by task, not difficulty
     ```
   - Manually review every 5 sessions (pin to JOURNAL.md)

2. **Skill self-improvement protocol**
   - In `.claude/skills/SKILL.md`, add a "Learnings" section
   - After using `/commit`, `/drawio`, etc., note what worked/failed
   - When Haiku runs next, it reads Learnings and refines the skill instructions
   - Example: `/commit` might learn "users prefer atomic commits over sweeping ones"

3. **Session-scoped context synthesis**
   - Create `.claude/session-notes/` for per-session learnings
   - At session end, summarize 1-2 key insights that future sessions should know
   - This mimics Hermes' FTS5 + summarization without changing your tools

**Effort**: Low (document discipline, not architecture)  
**Reversible**: Yes (just more markdown files)  
**Win**: You keep IDE integration + get Hermes-style memory hygiene  

---

### Path B: Run Hermes in parallel (Medium coupling)
**Use Hermes as a background autonomous agent; Claude Code for IDE work.**

**Use cases for Hermes:**
- **Between-session learning**: Run Hermes at end of day to review memory, create skills, summarize learnings
- **Async research**: "Hermes, research this pattern across past sessions and write a design doc"
- **Skill refinement**: Let Hermes improve skills independent of IDE
- **Messaging**: Answer HR questions from Slack via Hermes voice mode (while you code in VS Code)

**Integration points:**
- Hermes writes to `.claude/skills/` (shared skill directory with Claude Code)
- Memory lives in separate Hermes DB (SQLite)—you can export to Claude Code's MEMORY.md manually
- CLAUDE.md becomes shared config (both agents read it for principles)

**Effort**: Medium (install Hermes, configure MCP bridges)  
**Reversible**: Yes (separate process, doesn't touch your code)  
**Tradeoff**: Two systems means two mental models; need bridging discipline  

---

### Path C: Full Hermes migration (High coupling, future)
**Replace Claude Code with Hermes as primary agent; use Claude Code extensions for IDE integration.**

**When to consider**: After Ex3 (when you have an LLM pipeline). Hermes shines with autonomous skill creation from extraction failures.

**Lost**: IDE point-and-click; permission model changes (Hermes uses command approval, not tool allowlist)  
**Gained**: Full autonomy, evolving skills, cross-session learning, multi-channel (Slack/Discord/voice alongside CLI)  

**This is not recommended for Ex1-2.** Your current setup is fine.

---

## 4. Comparison Table

| Dimension | Claude Code | Hermes | Hybrid Path A | Hybrid Path B |
|-----------|-------------|--------|---------------|---------------|
| **IDE integration** | ✅ Native | ❌ CLI/messaging | ✅ Keeps it | ✅ Keeps it |
| **Memory** | Explicit (MEMORY.md) | Auto-curated | Explicit + manual synthesis | Explicit + async synthesis |
| **Skills** | Static docs | Autonomous improvement | Static docs + learnings section | Autonomous in Hermes, shared to Claude Code |
| **User modeling** | Manual (feedback memories) | Honcho dialectic (auto) | Manual | Auto in Hermes, manual review in Claude Code |
| **Cross-session recall** | Manual (read MEMORY.md) | FTS5 + LLM summary | Manual + per-session notes | Auto in Hermes, export on demand |
| **Cost awareness** | You decide routing | Built-in cost tracking | You decide (no change) | You decide + Hermes logs |
| **Permission model** | Tool allowlist | Command approval queue | Tool allowlist | Tool allowlist in Claude Code; approval in Hermes |
| **Setup effort** | 0 (you have it) | 2-3 hours | 1-2 hours (docs discipline) | 4-6 hours (install, bridge) |
| **Ongoing effort** | ~5 min/session | ~2 min/session (auto) | ~10 min/session (manual synthesis) | ~3 min/session (Claude Code) + 10 min/day (Hermes batch) |

---

## 5. Your Project (ABC HR Ex1-8): Which Path?

### Immediate (Ex1): Do nothing
Claude Code is perfect for UI-only JSON-backed work. No autonomous learning needed.

### Near-term (Ex2-3): Adopt Path A
Once you add FastAPI backend + LLM extraction pipeline:
1. Create `.claude/skills/commit-correct-attribution/` (your feedback already hints at this)
2. Add "Learnings" section to existing skills
3. Create `.claude/session-notes/` for per-session synthesis
4. Update MEMORY.md to consolidate feedback entries every 5 commits

**Why**: Extraction failures in Ex3 will generate lots of trial-and-error. Path A captures those learnings as skill improvements.

### Future (Ex5-6): Evaluate Path B
When you add embeddings & HR agent (Strands, Gmail MCP):
- Run Hermes as async "HR coordinator" (responds to Slack)
- Claude Code stays for coding
- Hermes learns from LLM extraction failures, creates skills for resume parsing, recruiter email templates, etc.

---

## 6. Claude Code Structure to Copy from roeyw5/claude-code-guide

Your CLAUDE.md is excellent. Here's what to layer in from the reference repo:

### Already have (keep as-is)
✅ Principles section (own every line, technician vs expert)  
✅ Architecture rules (data model pure, all reads via db.ts)  
✅ Schema discipline (stable IDs, optional fields nullable)  
✅ Stack conventions  
✅ Testing (test-first for data layer)  

### Add to CLAUDE.md (from guide patterns)
```markdown
## Skill Discipline
- Skills live in `.claude/skills/{name}/SKILL.md` with name and description frontmatter
- Each skill has a "Learnings" section for improvements discovered during use
- Skill names use kebab-case with prefixes: `commit-*`, `gen-*`, `review-*`

## Memory Synthesis
- Every 5 commits, review MEMORY.md and consolidate 3+ related entries into 1 principle
- Session notes live in `.claude/session-notes/{YYYY-MM-DD}.md` — one file per day
- Run `/memory-synthesize` (future CLI command) to auto-compact memory

## Hook Architecture
- Security hooks in `.claude/hooks/` follow PreToolUse pattern
- Logs go to `~/.claude/hooks-logs/` for audit trail
- Configurable severity levels (warn/block/allow)
```

### Skills to create (Path A)
1. **`commit-correct-attribution`**: Applies your feedback (drop hardcoded Haiku trailer, cite actual co-author)
2. **`model-routing-cost-aware`**: Documents Haiku/Sonnet/Opus split with cost rationale
3. **`session-synthesize`**: Distills 1-day session notes into learnings for MEMORY.md

---

## 7. Hermes Integration Patterns (If you pick Path B later)

**What Hermes excels at that Claude Code doesn't:**

1. **Multi-platform messaging**
   - Configure Hermes to respond in Slack: `@hermes what's the status of extraction pipeline?`
   - Voice mode: ask questions while coding
   - Same agent, any channel

2. **Batch operation**
   - `hermes batch --script analyze-extraction-failures.yaml`
   - Runs autonomously, logs to Hermes DB
   - Results exported to `.claude/batch-results/` for Claude Code to review

3. **Skill sharing (agentskills.io)**
   - Your `commit-correct-attribution` skill can be published and versioned
   - Other devs install: `hermes skills add @itaicarmeli/commit-correct-attribution`
   - Get updates automatically

4. **MCP bridging**
   - Hermes has built-in MCP support (70+ tools)
   - Can wire Gmail MCP → Hermes → Slack (Ex6 use case)
   - Claude Code uses MCP but doesn't auto-improve from failures

---

## 8. Concrete First Step (Recommended)

**Do this in Ex2 (when you add FastAPI):**

1. **Create `.claude/skills/commit-correct-attribution/SKILL.md`**
   ```markdown
   ---
   name: commit-correct-attribution
   description: Create commits with accurate author attribution (no hardcoded trailers)
   ---
   
   ## Purpose
   Ensure every commit cites real co-authors (not placeholder Haiku trailer).
   
   ## Instructions
   [... existing commit logic ...]
   
   ## Learnings
   - **Initially**: hardcoded `Co-Authored-By: Claude Haiku 4.5` — wrong
   - **Discovered**: actual model should be detected from context or asked
   - **Improved**: now checks .claude/settings.json for model, prompts if ambiguous
   ```

2. **Add to CLAUDE.md**
   ```markdown
   ## Commit Attribution
   Every commit co-author line must be accurate. Do not hardcode. 
   Reference: `.claude/skills/commit-correct-attribution/` for implementation.
   ```

3. **Create `.claude/session-notes/2026-05-26.md`**
   ```markdown
   # Session: 2026-05-26
   
   ## Key Learnings
   - Commit attribution matters more than I thought—errors leak into git blame
   - Model routing feedback is strong signal; capture in MEMORY.md immediately
   
   ## For Next Session
   - Remember: Haiku for repetitive, Sonnet for impl, Opus for planning
   - Create skill once pattern stabilizes (don't wait for perfection)
   ```

4. **Next session**: Review `.claude/session-notes/` at start. Update MEMORY.md if pattern holds.

---

## 9. Decision Framework

| Question | Path A | Path B | Path C |
|----------|--------|--------|--------|
| Keep IDE integration? | ✅ Yes | ✅ Yes | ❌ No |
| Need messaging platform? | ❌ | ✅ | ✅ |
| Have LLM pipeline yet? | ❌ | ✅ | ✅ |
| Want autonomous learning? | 🤔 Manual | ✅ | ✅ |
| Timeline for Ex1-3? | Start now | Wait for Ex5 | Don't do this |

---

## 10. Files to Create/Update

### Immediate (Path A)
- [ ] Update `.claude/CLAUDE.md` with Skill Discipline + Memory Synthesis sections
- [ ] Create `.claude/session-notes/` directory
- [ ] Create `.claude/session-notes/TEMPLATE.md` for daily notes
- [ ] Create `.claude/skills/commit-correct-attribution/SKILL.md` (formalize the feedback)
- [ ] Create `.claude/skills/model-routing-cost-aware/SKILL.md` (document the feedback)

### Future (Path B, Ex5+)
- [ ] Install Hermes (follow quickstart at hermes-agent.nousresearch.com)
- [ ] Create bridge MCP server mapping Hermes skills → Claude Code
- [ ] Set up Hermes Slack/messaging integration
- [ ] Export Hermes memory to MEMORY.md on sync

---

## References

**Claude Code Guide** (your reference)
- CLAUDE.md patterns: https://github.com/roeyw5/claude-code-guide/blob/main/CLAUDE.md
- Example agents: https://github.com/roeyw5/claude-code-guide/tree/main/.claude/agents/
- Skill structure: https://github.com/roeyw5/claude-code-guide/tree/main/.claude/skills/

**Hermes Harness** (future integration)
- Main docs: https://hermes-agent.nousresearch.com/docs
- Memory system: https://hermes-agent.nousresearch.com/docs/user-guide/features/memory
- Skills system: https://hermes-agent.nousresearch.com/docs/user-guide/features/skills
- Skills Hub: https://agentskills.io

**Your Project**
- CLAUDE.md: `/home/ic/bootcamp/ABC/CLAUDE.md` (excellent foundation)
- Memory: `/home/ic/.claude/projects/-home-ic-bootcamp-ABC/memory/`
- Feedback: [[feedback_commit-attribution.md]] and [[feedback_model-routing-cost.md]]

---

## Conclusion

**Hermes is powerful but orthogonal to Claude Code.** You don't have to choose. Start with **Path A** (memory synthesis + skill discipline in Claude Code—takes 1-2 hours), prove it works on Ex2-3, then **evaluate Path B** (parallel Hermes agent) if you hit repetitive LLM extraction patterns around Ex5.

Your project's CLAUDE.md is already excellent. The gap isn't architecture—it's **making skill learnings explicit and memory synthesizable**. Path A closes that gap without adding infrastructure.

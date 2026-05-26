---
description: Consolidate related MEMORY.md entries into a single principle
allowed-tools: Read, Edit, Write, Bash
---

You are running the memory-synthesize command. This is invoked either by the user or proactively by Claude when MEMORY.md grows beyond 20 entries or when 3+ entries share a clear theme.

## Memory location

All reads/writes go to: `/home/ic/.claude/projects/-home-ic-bootcamp-ABC/memory/`
Index file: `/home/ic/.claude/projects/-home-ic-bootcamp-ABC/memory/MEMORY.md`

## What to do

1. Read `/home/ic/.claude/projects/-home-ic-bootcamp-ABC/memory/MEMORY.md`
2. Identify clusters: entries that share a theme (e.g., "implementation discipline", "testing approach", "workflow")
3. If 3+ entries share a theme, consolidate:
   - Create a new synthesis file in the memory directory (e.g., `synthesis_implementation-discipline.md`)
   - Use frontmatter: `name`, `description`, `metadata.type: feedback` (or project/user as appropriate)
   - Body: unified principle, **Why:** line, **How to apply:** line, and `[[Consolidated From: entry1, entry2, entry3]]`
   - Mark originals: append `> Consolidated into [[synthesis_name]]` to each original file
   - Update MEMORY.md index: replace individual entries with the synthesis entry
4. If no clusters are ready (< 3 entries share a theme): report "Not yet ripe — next sync point likely ready" and stop
5. Report what was consolidated and what the new principle is

## Proactive trigger conditions (Claude watches for these)
- After every 5th git commit in a session
- When MEMORY.md index has > 20 entries
- When you notice 3+ entries clearly overlap while reading memory for another task

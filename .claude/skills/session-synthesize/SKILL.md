---
name: session-synthesize
description: Distill today's session note into MEMORY.md candidates at end of session
---

## Purpose
Session notes are ephemeral. This skill extracts the signal worth keeping before the note is archived.

## When to Use
End of session — after the last commit, before closing the editor. Also invoked by Claude automatically when it detects "end of session" signals (user says done, last commit of the day, long idle).

## Instructions

1. Read today's note: `.claude/session-notes/{YYYY-MM-DD}.md`
2. Scan for entries that meet any of these bars:
   - Appeared in 2+ sessions (repeating pattern)
   - Contradicted a prior MEMORY.md assumption (update needed)
   - Blocked work or caused a rework (principle-level learning)
3. For each candidate, propose a typed memory entry:
   - `feedback` — guidance about approach (what to do or avoid)
   - `project` — ongoing work, deadline, stakeholder constraint
   - `user` — something learned about how the user likes to work
4. Show the proposals. Ask: "Save any of these to MEMORY.md? (list numbers or 'none')"
5. For each confirmed: write the memory file + update MEMORY.md index
6. Archive the session note: move to `.claude/.archive/{YYYY-MM-DD}.md`
7. Log to `.claude/.skilllog`:
   ```json
   {"timestamp": "{ISO}", "event": "session-synthesized", "date": "{YYYY-MM-DD}", "promoted": N, "archived": true}
   ```

## What NOT to promote
- One-off workarounds that won't recur
- Things already in MEMORY.md or CLAUDE.md
- Implementation details (those belong in git history)

## Learnings

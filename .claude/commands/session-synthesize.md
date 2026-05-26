---
description: Distill today's session note into MEMORY.md candidates, then archive the note
allowed-tools: Read, Edit, Write, Bash
---

You are running the session-synthesize command. Invoke this at the end of a working session, or proactively when you detect end-of-session signals (user says "done", "wrapping up", "that's it for today", or after the last commit of a session with no further coding prompts).

## Memory location

All writes go to: `/home/ic/.claude/projects/-home-ic-bootcamp-ABC/memory/`
Index file: `/home/ic/.claude/projects/-home-ic-bootcamp-ABC/memory/MEMORY.md`

Do NOT create a MEMORY.md inside the project's `.claude/` directory.

## What to do

1. Find today's session note: `/home/ic/bootcamp/ABC/.claude/session-notes/{YYYY-MM-DD}.md`
   - If it doesn't exist or is empty: report that and stop
2. Read the note. Scan for entries that meet any of these bars:
   - Appeared in 2+ sessions (repeating pattern)
   - Contradicted a prior MEMORY.md assumption (update needed)
   - Blocked work or caused a rework (principle-level learning)
   - New preference or style confirmed by the user
3. Read current MEMORY.md to avoid proposing duplicates
4. For each candidate, propose a typed memory entry. Show them:
   ```
   [1] type: feedback — "Don't use PreToolUse for session start; use UserPromptSubmit + /tmp guard"
   [2] type: project  — "gen-drawio skill installed; infographic icon paths unverified"
   [3] type: user     — ...
   ```
5. Ask: "Save any of these? (numbers, 'all', or 'none')"
6. For each confirmed:
   - Write the memory file with correct frontmatter (`name`, `description`, `metadata.type`)
   - Body: rule/fact · **Why:** · **How to apply:**
   - Update MEMORY.md index with one-line entry
7. Archive the session note:
   ```bash
   mv /home/ic/bootcamp/ABC/.claude/session-notes/{YYYY-MM-DD}.md /home/ic/bootcamp/ABC/.claude/.archive/
   ```
8. Log to `.skilllog`:
   ```json
   {"timestamp": "{ISO}", "event": "session-synthesized", "date": "{YYYY-MM-DD}", "promoted": N, "archived": true}
   ```

## What NOT to promote
- One-off workarounds unlikely to recur
- Anything already in MEMORY.md or CLAUDE.md
- Implementation details (those live in git history)

## Proactive trigger conditions
- User signals end of session ("done for today", "wrapping up", "let's stop here")
- Last commit of the day followed by no further coding prompts for a while
- User explicitly asks to "save learnings" or "update memory"
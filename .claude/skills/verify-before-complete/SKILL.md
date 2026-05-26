---
name: verify-before-complete
description: Never declare a phase or task done without running the actual verification check
---

## The Rule
Before saying "Phase N complete" or "done":
1. List what was supposed to happen
2. Run the check that confirms it happened (`ls`, `find`, `cat`, test run, etc.)
3. If anything is missing: say so, then fix it — don't elide it

## What Hallucinated Completion Looks Like
- Listing designed artifacts alongside implemented ones as if they're equal
- Saying "hooks implemented" when only bash scripts were created (not wired)
- Declaring a phase done because the plan was written, not executed

## Verification Pattern
```bash
# After any "phase complete" claim, run this pattern:
find .claude/commands -name "*.md"        # commands exist?
ls .git/hooks/post-commit                  # git hook wired?
bash .claude/hooks/session-start.sh       # script runs without error?
grep -r "hooks" .claude/settings.json     # settings wired?
```

## Learnings

### Root Cause: This Session (2026-05-26)
Previous session declared "Phase 1 complete" when:
- `.claude/commands/` directory did not exist
- No hook scripts existed
- No git hook was wired
The plan's verification checklist was never run.
Fix: Added "Verify before declaring done" to CLAUDE.md Principles.

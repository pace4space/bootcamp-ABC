---
description: Formalize a repeated pattern into a new skill file
allowed-tools: Read, Edit, Write, Bash
---

You are running the skill-new command. This is invoked either by the user (passing a skill name) or proactively by Claude when it detects a pattern that has appeared 3+ times in session notes or .skilllog.

## What to do

1. Determine the skill name:
   - If user passed an argument (e.g., `/skill-new fastapi-crud`), use that
   - If invoked proactively, name it from the detected pattern
2. Check `.claude/skills/` — abort if the skill already exists
3. Create the directory and SKILL.md: `.claude/skills/{name}/SKILL.md`
4. Use this structure:
   ```markdown
   ---
   name: {name}
   description: {one-line what and why}
   ---

   ## Purpose
   {Problem it solves}

   ## When to Use
   {Trigger condition — when should Claude use this?}

   ## Instructions
   {Numbered steps}

   ## Learnings
   {Leave empty — auto-populated from .skilllog errors}
   ```
5. Add an entry to MEMORY.md index under a "Skills" section if one exists, or append it
6. Append to `.claude/.skilllog`:
   ```json
   {"timestamp": "{ISO}", "event": "skill-created", "skill": "{name}", "trigger": "{why it was created}"}
   ```
7. Report: skill name, file path, what triggered its creation

## Proactive trigger conditions (Claude watches for these)
- When reviewing session notes and a pattern appears that has occurred 3+ times without a skill
- When `.skilllog` shows 3+ similar errors with no corresponding skill to fix them
- When user does the same manual workaround 2+ times in one session

## What NOT to do
- Do not create a skill for a one-off fix
- Do not create skills for things already in CLAUDE.md principles
- Do not create a skill that is just a restatement of existing Tailwind/React/TypeScript conventions

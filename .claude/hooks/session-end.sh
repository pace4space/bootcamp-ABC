#!/usr/bin/env bash
# Runs on Stop event. Auto-fills "Commits This Session" in today's session note.
# Also emits a reminder if Key Learnings still has template text.

TODAY=$(date +%Y-%m-%d)
REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel 2>/dev/null)" || exit 0
NOTE_PATH="$REPO_ROOT/.claude/session-notes/${TODAY}.md"

[ -f "$NOTE_PATH" ] || exit 0

python3 - "$NOTE_PATH" "$REPO_ROOT" "$TODAY" <<'PYEOF'
import sys, subprocess, re

note_path, repo_root, today = sys.argv[1], sys.argv[2], sys.argv[3]

result = subprocess.run(
    ['git', '-C', repo_root, 'log', '--oneline', f'--after={today} 00:00', '--format=- `%h` %s'],
    capture_output=True, text=True
)
commits = result.stdout.strip() or '- (none yet today)'

content = open(note_path).read()

marker = '## Commits This Session'
idx = content.find(marker)
if idx == -1:
    sys.exit(0)

# Body starts on the line immediately after the header line
body_start = idx + len(marker)
if body_start < len(content) and content[body_start] == '\n':
    body_start += 1

# Body ends at the \n that precedes the next ## header, or EOF.
# Keep that \n in content[body_end:] so inter-section blank lines are preserved.
next_section = re.search(r'\n## ', content[body_start:])
body_end = body_start + next_section.start() if next_section else len(content)

new_content = content[:body_start] + commits + '\n' + content[body_end:]
if new_content != content:
    open(note_path, 'w').write(new_content)
PYEOF

# Remind if learnings still has template placeholder
if grep -q "Insight 1\|Insight 2" "$NOTE_PATH" 2>/dev/null; then
  echo "SESSION NOTE: Key Learnings still has template text — fill before closing: $NOTE_PATH"
fi

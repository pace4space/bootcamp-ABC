#!/usr/bin/env bash
# Runs after each git commit. Logs to .skilllog and checks 5-commit cadence.

HOOK_DIR="$(dirname "$0")"
SKILLLOG="$HOOK_DIR/../.skilllog"
TODAY=$(date +%Y-%m-%d)

# Count commits today
COMMIT_COUNT=$(git log --oneline --after="$TODAY 00:00" 2>/dev/null | wc -l | tr -d ' ')
COMMIT_HASH=$(git rev-parse --short HEAD)
COMMIT_MSG=$(git log -1 --format="%s")

# Log the commit event
printf '{"timestamp":"%s","event":"commit","hash":"%s","message":"%s","daily_count":%s}\n' \
  "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$COMMIT_HASH" "$COMMIT_MSG" "$COMMIT_COUNT" \
  >> "$SKILLLOG"

# At every 5th commit, emit a reminder Claude will see in next tool output
if [ $((COMMIT_COUNT % 5)) -eq 0 ] && [ "$COMMIT_COUNT" -gt 0 ]; then
  echo "SKILLABILITY: Commit $COMMIT_COUNT today — memory synthesis check recommended (/memory-synthesize)"
fi

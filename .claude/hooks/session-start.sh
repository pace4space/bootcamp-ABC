#!/usr/bin/env bash
# Creates today's session note once per day. Guard prevents re-running.

TODAY=$(date +%Y-%m-%d)
GUARD="/tmp/skillability_session_${TODAY}"

[ -f "$GUARD" ] && exit 0  # already ran today

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NOTE_PATH="${SCRIPT_DIR}/../session-notes/${TODAY}.md"
TEMPLATE="${SCRIPT_DIR}/../session-notes/TEMPLATE.md"

if [ ! -f "$NOTE_PATH" ] && [ -f "$TEMPLATE" ]; then
  cp "$TEMPLATE" "$NOTE_PATH"
  sed -i "s/YYYY-MM-DD/$TODAY/g" "$NOTE_PATH"
fi

touch "$GUARD"

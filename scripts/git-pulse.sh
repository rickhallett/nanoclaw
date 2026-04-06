#!/usr/bin/env bash
# git-pulse — aggregate git activity across ~/code repos
# Usage: git-pulse [days] [--compact]
# Default: today's commits. Pass a number for N days back.

set -euo pipefail

DAYS="${1:-0}"
COMPACT="${2:-}"
CODE_DIR="${HOME}/code"
AUTHOR="Rick Hallett"

if [ "$DAYS" -eq 0 ]; then
  SINCE="midnight"
  LABEL="today"
else
  SINCE="${DAYS} days ago"
  LABEL="last ${DAYS} days"
fi

total=0
output=""

for repo in "${CODE_DIR}"/*/; do
  [ -d "${repo}.git" ] || continue
  name=$(basename "$repo")

  commits=$(git -C "$repo" log --oneline --since="$SINCE" --author="$AUTHOR" --format="%h %s" 2>/dev/null || true)
  [ -z "$commits" ] && continue
  count=$(echo "$commits" | wc -l | tr -d ' ')

  total=$((total + count))

  if [ -n "$COMPACT" ]; then
    output+="${name} (${count}) "
  else
    output+="$(printf '\n=== %s (%d) ===\n%s\n' "$name" "$count" "$commits")"
  fi
done

if [ -n "$COMPACT" ]; then
  echo "${total} commits ${LABEL}: ${output}"
else
  echo "--- git pulse: ${total} commits ${LABEL} ---"
  if [ "$total" -eq 0 ]; then
    echo "No commits found."
  else
    echo "$output"
  fi
fi

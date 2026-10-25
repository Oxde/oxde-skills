#!/usr/bin/env bash
# feedctl for Hermes agents: loads FEED_URL/FEED_TOKEN from the profile env if the shell lacks them,
# finds the oxde-skills checkout, and runs `python3 -m feed.feedctl "$@"`.
#   bash ~/.hermes/profiles/writer/scripts/feed-ctl.sh set-status <id> shown --insight "..." --why "..."
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
if [ -z "${FEED_URL:-}" ] || [ -z "${FEED_TOKEN:-}" ]; then
  ENV_FILE="${HERMES_PROFILE_ENV:-$HOME/.hermes/profiles/writer/.env}"
  if [ -f "$ENV_FILE" ]; then
    # Only these two keys; the env file has unquoted values that break plain sourcing.
    while IFS='=' read -r k v; do
      case "$k" in FEED_URL|FEED_TOKEN) export "$k=$v";; esac
    done < <(grep -E '^(FEED_URL|FEED_TOKEN)=' "$ENV_FILE")
  fi
fi
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.feedctl "$@"

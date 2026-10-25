#!/usr/bin/env bash
# Hermes --script for the feed-menu job: prints the next research menu as markdown.
# Stable output on an empty feed ("Research menu: nothing new.") so --monitor-script can suppress the agent.
set -euo pipefail
# Works both from the Git checkout and as a copy inside a Hermes profile's scripts directory.
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
if [ -z "${FEED_URL:-}" ] || [ -z "${FEED_TOKEN:-}" ]; then
  ENV_FILE="${HERMES_PROFILE_ENV:-$HOME/.hermes/profiles/writer/.env}"
  if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r k v; do case "$k" in FEED_URL|FEED_TOKEN|GH_TOKEN) export "$k=$v";; esac; done < <(grep -E '^(FEED_URL|FEED_TOKEN|GH_TOKEN)=' "$ENV_FILE")
  fi
fi
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.feedctl menu --quota "${FEED_QUOTA:-news=3,skill=2,repo=2,post=2}"

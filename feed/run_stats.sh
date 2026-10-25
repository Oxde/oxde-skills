#!/usr/bin/env bash
# Hermes --no-agent --script for the weekly feed-stats job.
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
exec "${PYTHON:-python3}" -m feed.feedctl stats --days "${FEED_STATS_DAYS:-7}"

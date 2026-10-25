#!/usr/bin/env bash
# Hermes --no-agent --script for the weekly feed-stats job.
set -euo pipefail
# Works both from the Git checkout and as a copy inside a Hermes profile's scripts directory.
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.feedctl stats --days "${FEED_STATS_DAYS:-7}"

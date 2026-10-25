#!/usr/bin/env bash
# Runs every producer and posts the result to the feed service. Same command Railway cron runs.
set -euo pipefail
# Works both from the Git checkout and as a copy inside a Hermes profile's scripts directory.
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.collect

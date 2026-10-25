#!/usr/bin/env bash
# Hermes --script for the feed-menu job: prints the next research menu as markdown.
# Stable output on an empty feed ("Research menu: nothing new.") so --monitor-script can suppress the agent.
set -euo pipefail
# Works both from the Git checkout and as a copy inside a Hermes profile's scripts directory.
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.feedctl menu --quota "${FEED_QUOTA:-news=4,skill=2,repo=2}"

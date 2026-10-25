#!/usr/bin/env bash
# Hermes --script for the feed-menu job: prints the next research menu as markdown.
# Stable output on an empty feed ("Research menu: nothing new.") so --monitor-script can suppress the agent.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m feed.feedctl menu --quota "${FEED_QUOTA:-news=4,skill=2,repo=2}"

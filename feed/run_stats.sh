#!/usr/bin/env bash
# Hermes --no-agent --script for the weekly feed-stats job.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m feed.feedctl stats --days "${FEED_STATS_DAYS:-7}"

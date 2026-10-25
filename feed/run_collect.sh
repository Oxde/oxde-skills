#!/usr/bin/env bash
# Runs every producer and posts the result to the feed service. Same command Railway cron runs.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -m feed.collect

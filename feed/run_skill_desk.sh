#!/usr/bin/env bash
# Hermes --script for the skill-desk job: prints the top skill/repo candidates without offering them.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
if [ -z "${FEED_URL:-}" ] || [ -z "${FEED_TOKEN:-}" ]; then
  ENV_FILE="${HERMES_PROFILE_ENV:-$HOME/.hermes/profiles/writer/.env}"
  if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r k v; do case "$k" in FEED_URL|FEED_TOKEN|GH_TOKEN) export "$k=$v";; esac; done < <(grep -E '^(FEED_URL|FEED_TOKEN|GH_TOKEN)=' "$ENV_FILE")
  fi
fi
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.feedctl top --lanes "${SKILL_DESK_LANES:-skill,repo}" --n "${SKILL_DESK_N:-6}"

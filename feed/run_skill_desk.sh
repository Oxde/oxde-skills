#!/usr/bin/env bash
# Hermes --script for the skill-desk job: prints the top skill/repo candidates without offering them.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." 2>/dev/null && pwd)"
[ -f "$ROOT/feed/feedctl.py" ] || ROOT="${OXDE_SKILLS:-$HOME/AI-Agent-Media-Business/oxde-skills}"
cd "$ROOT"
exec "${PYTHON:-python3}" -m feed.feedctl top --lanes "${SKILL_DESK_LANES:-skill,repo}" --n "${SKILL_DESK_N:-6}"

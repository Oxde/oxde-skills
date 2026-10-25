#!/usr/bin/env bash
# Deploy the feed service + dashboard to Railway (project linkedin_agent, service linkedin-writer).
# Assembles a small staging directory so the upload root holds the Dockerfile, then `railway up`.
# Needs RAILWAY_TOKEN (the project token) in the environment. Never prints it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE="${RAILWAY_SERVICE:-linkedin-writer}"
: "${RAILWAY_TOKEN:?RAILWAY_TOKEN (project token) is required}"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/feed-deploy.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
cp "$ROOT/linkedin/Dockerfile" "$ROOT/linkedin/railway.toml" "$STAGE/"
rsync -a --exclude '__pycache__' --exclude 'tests' --exclude '*.db*' "$ROOT/feed/" "$STAGE/feed/"
rsync -a "$ROOT/linkedin/apps/linkedin-dashboard/public/" "$STAGE/public/"
echo "deploying $(du -sh "$STAGE" | cut -f1) from staging to service $SERVICE"
cd "$STAGE"
railway up --service "$SERVICE" --ci "$@"

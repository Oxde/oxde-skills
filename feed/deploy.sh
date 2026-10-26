#!/usr/bin/env bash
# Deploy the feed service + dashboard to Railway (project linkedin_agent, service linkedin-writer).
# Assembles a small staging directory so the upload root holds the Dockerfile, then `railway up`.
# Needs RAILWAY_TOKEN (the project token) in the environment. Never prints it.
# Usage: deploy.sh            → the feed service + dashboard (service linkedin-writer)
#        deploy.sh --collect  → the collection cron (service feed-collect): same image, start
#                               command `python -m feed.collect`, schedule from railway.collect.toml
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MODE="${1:-service}"
if [ "$MODE" = "--collect" ]; then
  SERVICE="${RAILWAY_SERVICE:-feed-collect}"; TOML="$ROOT/linkedin/railway.collect.toml"
else
  SERVICE="${RAILWAY_SERVICE:-linkedin-writer}"; TOML="$ROOT/linkedin/railway.toml"
fi
: "${RAILWAY_TOKEN:?RAILWAY_TOKEN (project token) is required}"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/feed-deploy.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
cp "$ROOT/linkedin/Dockerfile" "$STAGE/" && cp "$TOML" "$STAGE/railway.toml"
rsync -a --exclude '__pycache__' --exclude 'tests' --exclude '*.db*' "$ROOT/feed/" "$STAGE/feed/"
rsync -a "$ROOT/linkedin/apps/linkedin-dashboard/public/" "$STAGE/public/"
echo "deploying $(du -sh "$STAGE" | cut -f1) from staging to service $SERVICE"
cd "$STAGE"

railway up --service "$SERVICE" --ci

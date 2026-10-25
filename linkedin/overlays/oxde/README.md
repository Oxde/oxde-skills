# Oxde LinkedIn overlay

This directory combines the portable `linkedin/` core with Mark/Oxde's non-secret operating rules.

## Included

- voice, anti-slop, source, visual, and editorial rules
- the four-queue growth system
- source collector for Telegram/RSS leads
- local own-post metric collector through an authenticated browser bridge
- Railway dashboard source and deployment configuration in `linkedin/apps/linkedin-dashboard/`

## Deliberately excluded

- API keys, Railway tokens, Maton keys, browser cookies, and OAuth sessions
- post archives, private drafts, raw session history, and MyBrain content outside the LinkedIn writing scope
- scheduled-job state; recreate schedules in the target agent environment from the contract below

## Environment-specific settings

`overlays/oxde/scripts/collect_linkedin_metrics.py` defaults to Mark's public LinkedIn activity page and local vault paths. For another user, set:

```text
LINKEDIN_ACTIVITY_URL=https://www.linkedin.com/in/<vanity>/recent-activity/all/
LINKEDIN_METRICS_DIR=/durable/path/own-post-metrics
```

The scripts require a normal LinkedIn login in the user's persistent browser session. Never accept credentials or browser cookies through chat.

## Scheduler contract

The portable canonical behavior is versioned in [`cron/editorial-radar.md`](cron/editorial-radar.md). Hermes job IDs, delivery destinations, tool grants, and working directories are intentionally host-local.

- 09:00: own-post performance digest, read-only
- 10:00 and 16:00: Editorial Radar (source leads + primary verification + compact niche signal)
- every 15 minutes while an item is genuinely active: ask for the smallest decision; never auto-publish
- every 30 minutes 08:00–22:30: collect own-post visible metrics locally

All social writes remain explicit-approval-only. Publishing requires the exact approved text and a hash guard.

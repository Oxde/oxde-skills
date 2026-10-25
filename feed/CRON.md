# Feed cron contract

Canonical schedules for the research feed. Host-local job IDs, chat IDs, and tokens are never
committed; each host recreates the jobs from this file. Replaces
`linkedin/overlays/oxde/cron/editorial-radar.md` and `radar/CRON.md` (kept for one proving week).

## Environment

In the Hermes `writer` profile `.env` on the laptop:

```
FEED_URL=https://<railway domain of the linkedin-writer service>
FEED_TOKEN=<same value as the FEED_TOKEN variable on that Railway service>
GH_TOKEN=<optional, raises the GitHub search rate limit>
```

Scripts are symlinked from the Git checkout into the profile's scripts directory:

```bash
cd ~/.hermes/profiles/writer/scripts
ln -sf ~/AI-Agent-Media-Business/oxde-skills/feed/run_menu.sh feed-run_menu.sh
ln -sf ~/AI-Agent-Media-Business/oxde-skills/feed/run_collect.sh feed-run_collect.sh
ln -sf ~/AI-Agent-Media-Business/oxde-skills/feed/run_stats.sh feed-run_stats.sh
mkdir -p ../skills/feed && cp ~/AI-Agent-Media-Business/oxde-skills/feed/SKILL.md ../skills/feed/SKILL.md
```

## Jobs (profile `writer`)

| job | schedule | mode | what |
|---|---|---|---|
| `feed-menu` | `30 9,16 * * *` | agent + monitor | prints the menu, runs the agent only when it changed, sends the Telegram menu |
| `feed-collect` | `0 9,15 * * *` | `--no-agent`, paused when Railway cron is on | runs the producers against the hosted service |
| `feed-stats` | `0 18 * * 0` | `--no-agent` | weekly stats to Telegram |

```bash
hermes -p writer cron create "30 9,16 * * *" --name feed-menu \
  --script feed-run_menu.sh --monitor-script feed-run_menu.sh \
  --skill feed --skill linkedin-writer --skill linkedin-hooks \
  --deliver origin --failure-deliver origin \
  "$(cat ~/AI-Agent-Media-Business/oxde-skills/feed/prompts/menu.md)"

hermes -p writer cron create "0 9,15 * * *" --name feed-collect --no-agent \
  --script feed-run_collect.sh --deliver local --failure-deliver origin

hermes -p writer cron create "0 18 * * 0" --name feed-stats --no-agent \
  --script feed-run_stats.sh --deliver origin
```

Monitor mode hashes the script output; `Research menu: nothing new.` is stable, so an empty feed
costs no model call. A `--no-agent` job with empty stdout is silent; `feed-collect` prints one
summary line, delivered to `local` (the log), and failures go to Telegram.

## Railway cron (when enabled)

A second service `feed-collect` in project `linkedin_agent`, same image, start command
`python -m feed.collect`, cron schedule `0 7,13 * * *` (UTC; 09:00 and 15:00 Amsterdam in
winter), variables `FEED_URL` (the internal URL of `linkedin-writer`) and `FEED_TOKEN`. When it is
on, pause the Hermes `feed-collect` job; when it is off, resume it. Creating that service is a
billable resource and needs Mark's go-ahead.

## Retired jobs

Pause, do not delete, for the proving week: the writer-profile "LinkedIn Editorial Radar" and the
default-profile "Skill Radar". The metric collector and the post-performance digest keep running.

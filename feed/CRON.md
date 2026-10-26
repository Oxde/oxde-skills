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

Scripts are **copied** (Hermes rejects symlinks that resolve outside its scripts directory)
from the Git checkout into the profile's scripts directory; each copy finds the checkout through
`OXDE_SKILLS` (default `~/AI-Agent-Media-Business/oxde-skills`). Re-copy after every pull.

```bash
R=~/AI-Agent-Media-Business/oxde-skills; S=~/.hermes/profiles/writer/scripts
for f in run_menu run_collect run_stats run_skill_desk ctl; do cp $R/feed/$f.sh $S/feed-$f.sh; done
mkdir -p $S/../skills/skill-posts && cp $R/linkedin/skills/skill-posts/*.md $S/../skills/skill-posts/
mkdir -p $S/../skills/feed && cp $R/feed/SKILL.md $S/../skills/feed/SKILL.md
```

## Jobs (profile `writer`)

| job | schedule | mode | what |
|---|---|---|---|
| `feed-menu` | `30 9,16 * * *` | agent | prints the menu into the prompt; the agent replies `[SILENT]` on `nothing new` |
| `feed-collect` | `0 9,15 * * *` | `--no-agent`, paused when Railway cron is on | runs the producers against the hosted service |
| `feed-stats` | `0 18 * * 0` | `--no-agent` | weekly stats to Telegram |
| `skill-desk` | `0 11 * * 2,4` | agent + `skill-posts` | judges the top skill/repo candidates against the known option, reports 2–3 with verdicts, marks the generic ones skipped with the reason |

```bash
hermes -p writer cron create "30 9,16 * * *" --name feed-menu \
  --script feed-run_menu.sh \
  --deliver telegram --failure-deliver telegram \
  "$(cat ~/AI-Agent-Media-Business/oxde-skills/feed/prompts/menu.md)"

hermes -p writer cron create "0 9,15 * * *" --name feed-collect --no-agent \
  --script feed-run_collect.sh --deliver local --failure-deliver telegram

hermes -p writer cron create "0 18 * * 0" --name feed-stats --no-agent \
  --script feed-run_stats.sh --deliver telegram

hermes -p writer cron create "0 11 * * 2,4" --name skill-desk \
  --script feed-run_skill_desk.sh --skill skill-posts \
  --deliver telegram --failure-deliver telegram \
  "$(cat ~/AI-Agent-Media-Business/oxde-skills/feed/prompts/skill_desk.md)"
```

`skill-desk` is the second pipeline next to the news menu: it reads score-ordered candidates
through `feedctl top` (which does **not** mark them offered), judges each against the best-known
option in its category, reports two or three with a verdict, and marks the generic ones
`skipped` with the reason so they never return. Mark answers "draft 2", "test 2" or "skip" in the
same chat; the writer skill and `skill-posts` carry the drafting. The LinkedIn Writer skill is not
attached to the desk any more: judging needs the repo page, not the voice rules (that cut the
prompt from 42k to about 12k characters).

`feed-menu` attaches **no skills**: the writer skills add ~45k characters of context the menu
job never uses, and the `feed` skill is for the main chat agent that handles Mark's pick (it is
installed in the profile's skills directory, so that agent loads it on demand).

`--monitor-script` is deliberately not used on `feed-menu`: the monitor would run the menu
script a second time per tick and count an extra offer on every item. An empty menu is one cheap
model call that ends in `[SILENT]`. A `--no-agent` job with empty stdout is silent; `feed-collect`
prints one summary line, delivered to `local` (the log), and failures go to Telegram.

## Railway cron (enabled 2026-10-26)

Service `feed-collect` in project `linkedin_agent`, deployed with `bash feed/deploy.sh --collect`.
Its start command `python -m feed.collect`, cron `0 7,13 * * *` (UTC) and restart policy
`NEVER` are set on the service instance itself (the staged `railway.collect.toml` was not
honoured by `railway up`; set them through the API with `serviceInstanceUpdate` if they are ever
lost). Variables: `FEED_URL=http://linkedin-writer.railway.internal:8080`,
`FEED_TOKEN=${{linkedin-writer.FEED_TOKEN}}`, `APIFY_API_KEY`. The Hermes `feed-collect` job is
paused while this runs.

## Railway cron (original note)

A second service `feed-collect` in project `linkedin_agent`, same image, start command
`python -m feed.collect`, cron schedule `0 7,13 * * *` (UTC; 09:00 and 15:00 Amsterdam in
winter), variables `FEED_URL` (the internal URL of `linkedin-writer`) and `FEED_TOKEN`. When it is
on, pause the Hermes `feed-collect` job; when it is off, resume it. Creating that service is a
billable resource and needs Mark's go-ahead.

## Retired jobs

Pause, do not delete, for the proving week: the writer-profile "LinkedIn Editorial Radar" and the
default-profile "Skill Radar". The metric collector and the post-performance digest keep running.

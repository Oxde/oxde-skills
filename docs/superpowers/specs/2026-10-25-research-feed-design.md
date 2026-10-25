# Research Feed: one daily topic feed for LinkedIn posts (and later videos)

Date: 2026-10-25. Status: approved by Mark 2026-10-25. Hosted on Railway from the start (the writer-profile project token was verified working via the Railway CLI). Branch: `oxde`.

## 1. Intent

Mark produces content in two places: LinkedIn posts (news, opinions, useful skills) and short
videos on Instagram/TikTok (explaining skills and facts). Today two Hermes cron jobs on the
second laptop already scout sources, but each run starts from zero, keeps no memory of what it
showed, and the LinkedIn job throws most leads away through a "one candidate or silent" gate.
The result is that Mark does not get a steady stream of things to react to.

The goal is a system where Mark's agents do the research and Mark only chooses. Every day he
gets a short menu in Telegram of candidates worth his voice; he picks one by talking to Hermes
("yeah, make a news post about the second one"); the existing LinkedIn writer turns it into a
post in his style. Target time for LinkedIn: about 15 minutes a day. Output target: two or three
posts a day across lanes (for example one news, one skill, one opinion), as a ceiling, not a quota.

Video ideas come from the same feed in a second phase.

## 2. Goals

- One **feed**: a durable local store of research items, each tagged with a lane, that
  remembers what was collected and what was already shown or picked.
- Several **producers** that write into the feed on a schedule: news (RSS, Telegram channels),
  skills (ClawHub, skills.sh), repos (GitHub), and later videos from followed creators.
- One **LinkedIn menu** job: twice a day, reads the unseen top items, writes a scannable
  Telegram message with several candidates, each with a link, a one-line "why Mark", and the
  extracted useful insight where it exists.
- A **pick loop**: Mark answers in natural language in the Hermes Telegram chat; Hermes marks
  the item picked and hands it to the existing writer flow (`linkedin/SKILL.md` + overlay rules).
- Code and prompts versioned in Git; the laptop only runs them.
- **Hostable from day one.** The feed is a small service that runs identically on Railway and
  on a laptop. Mark already hosts the LinkedIn dashboard on Railway and may later sell the
  LinkedIn agent as a service, so the feed must not depend on one machine's filesystem.

## 3. Non-goals and anti-goals

Non-goals (not in this build):

- Instagram competitor tracking. The Cutroom scout extension already captures reels manually;
  an automatic Instagram fetcher is parked.
- Video script generation. Phase two consumes the same feed; this design only ensures the feed
  carries what video needs (lane, insight, source).
- Public "AI news channel" on Telegram. Noted as a possible future consumer of the same feed.
- Paid LinkedIn data providers. Unchanged from today.
- Multi-tenant "LinkedIn agent as a service". Not in this build. The feed service gets an
  `owner` column from the start so that adding tenants later is a filter, not a migration,
  but there is one owner, no accounts, no billing.

Anti-goals (would make this a failure even if it works):

- Auto-publishing anything. Every post, comment, reaction stays approval-gated as today.
- A menu that is long, generic, or repeats items from yesterday. If Mark stops reading it, the
  system failed.
- Installing or executing scouted skills or repos during scheduled runs.
- Secrets, cookies, or Hermes job IDs committed to Git.

## 4. Constraints

- Runs on the second laptop under Hermes Agent (GPT models, sometimes fast/cheap ones). LLM
  work per run must stay small: heuristics first, one LLM pass over at most ~40 items.
- Python 3 standard library only for collectors and the feed service (sqlite3, http.server,
  urllib), matching the two existing scripts and the dashboard's current Dockerfile. No new
  Python dependencies without Mark's go-ahead.
- Hosting target is the existing Railway project `linkedin_agent` (service `linkedin-writer`,
  env `production`) that serves the LinkedIn dashboard (`linkedin/Dockerfile` + `railway.toml`).
  The feed service replaces the static file server in that image and keeps serving the
  dashboard. Deploys run from the laptop over SSH with the project token in the writer
  profile's env (`RAILWAY_TOKEN=… railway up`); the token never leaves the laptop. That token
  cannot change the service's GitHub binding, so deploys are `railway up` from the checkout,
  not auto-deploy from a branch.
- Delivery is Telegram through Hermes `--deliver telegram:<chat>`, into the same chat where Mark
  already talks to the Hermes main agent, so the reply "news post about 2" lands where the menu
  was sent. Picking is conversational.
- The LinkedIn writer and publish flow already run inside Hermes on the laptop (Mark: "I already
  have that in Hermes"). The feed, the menu, the pick and the writer are therefore all on one
  machine; no cross-machine hand-off. Video production stays in Claude on the main Mac and only
  reads feed exports in phase two.
- Mark's laptop is reachable by SSH as `hermes-mac` (verified 2026-10-25); Claude registers
  and tests jobs there. See `docs/laptop-runner-ssh.md`.
- Hermes facts, inspected live: v0.22.5, model `gpt-5.6-terra` through the openai-codex
  provider. The LinkedIn jobs live in the `writer` profile, the Skill Radar in the default
  profile. A job's `--script` must be a path under that profile's `~/.hermes/scripts/`, so the
  feed scripts are symlinked there from the Git checkout at
  `~/AI-Agent-Media-Business/oxde-skills`. All new jobs go in the `writer` profile so the pick
  reply lands in the chat that already has the LinkedIn writer skills.
- Hermes cron offers `--no-agent` (script only, no LLM), `--monitor-script` (skip the agent
  when the script output hash is unchanged), `--workdir`, and a per-job `notepad` key-value
  store. The producers run as a `--no-agent` job; the menu job uses `--monitor-script` on the
  menu output so an empty or unchanged feed costs no LLM call.
- Finding from the live run history: the Editorial Radar failed on every run from 2026-10-17
  to 2026-10-21 (Codex rejected the pinned model) and ran once with unknown result on 10-24.
  Nobody was told. The weekly stats job in this design exists partly so silent failure like
  that is visible; failures also set `--failure-deliver` to the Telegram chat.
- Existing contracts stay valid: `linkedin/overlays/oxde/cron/editorial-radar.md` and
  `radar/CRON.md` are rewritten to describe the new jobs, not deleted.

## 5. Design

### 5.1 The feed service

One Python process, standard library only, that owns a SQLite file and exposes a small HTTP
API plus the existing dashboard. Hosted on Railway in service `linkedin-writer` with a
persistent volume mounted at `/data` (`FEED_DB=/data/feed.db`). Run locally with
`FEED_DB=./feed.db` on port 4872. The same code and Dockerfile serve both.

| route | method | purpose |
|---|---|---|
| `/` and static files | GET | the dashboard, now reading live data from the API below |
| `/api/ingest` | POST | JSON lines from a producer; dedupes; returns counts |
| `/api/menu?quota=news=4,skill=2,repo=2` | GET | unseen top items per lane; marks them `offered` |
| `/api/items?status=&lane=&since=` | GET | list and search |
| `/api/items/{id}` | PATCH | status, insight, why, pick_note |
| `/api/stats?days=7` | GET | per-lane counts and source pick rates |

Writes require `Authorization: Bearer $FEED_TOKEN`; reads of `/api/stats` and `/api/items` are
also token-gated so the dashboard sends the token from a login field stored in the browser.
No token in Git. One table `items`:

| column | meaning |
|---|---|
| id | stable hash of canonical URL |
| owner | `oxde` for now; reserved for a future multi-tenant version |
| lane | `news`, `skill`, `repo`, `post`, `video` |
| source | producer name and origin, e.g. `rss:techcrunch`, `clawhub:trending`, `tg:data_secrets` |
| title, url, summary | as collected; summary is the raw excerpt, not LLM text |
| published_at, collected_at | ISO timestamps |
| score | heuristic 0–100 from the producer |
| metrics | JSON of raw counts per run (installs, stars, downloads) so velocity can be computed |
| insight | one or two lines written by the menu job's LLM pass; empty until then |
| status | `new`, `offered`, `shown`, `picked`, `drafted`, `posted`, `skipped`, `expired` |
| shown_at, picked_at | when status changed |
| pick_note | Mark's words when he picked it (verbatim, from Hermes) |

Status meaning (Claude's call, after builder review): `menu` marks the items it prints as
`offered`. Only items the agent actually lists in the Telegram message become `shown`, written
back by the agent. An `offered` item the agent dropped is eligible again for the next two
menus, then expires. "No repeats" in the definition of done means no item is `shown` twice.

Dedupe is by `id` plus a title-similarity check within the same lane over the last 7 days.
Items older than 14 days with status `new`, `offered` or `shown` become `expired`.

`feed/feedctl.py` is a thin stdlib HTTP client over that API with the same verbs: `ingest`
(stdin JSON lines), `menu --quota news=4,skill=2,repo=2` (prints the menu as markdown; a lane
with too few items gives its slots to the others), `pick <id> [--note]`, `set-status`,
`stats`. It reads `FEED_URL` and `FEED_TOKEN` from the environment. Per-lane quota is Claude's
call: lane scores are not comparable, and a global top-N would give an all-news menu on a busy
news day.

One Hermes job in the `writer` profile, `feed-menu`, at 09:30 and 16:00, with `--script
feed-run_menu.sh` (runs `feedctl menu` against the hosted service and prints it) and no skills
attached. Monitor mode was dropped after the first live run: it would run the menu script twice
per tick and count an extra offer on every item; an empty menu is one cheap model call ending in
`[SILENT]`. Scripts are copies in the profile's scripts directory (Hermes rejects symlinks that
resolve outside it) and locate the checkout themselves; `feed-ctl.sh` loads `FEED_URL` and
`FEED_TOKEN` from the profile env because the agent's shell has neither. See `feed/CRON.md`. The agent writes status back through its terminal tool. Whether the
scheduled job has that tool grant is checked over SSH during setup; if it does not, the agent
ends its message with a fenced JSON block and the next `run_menu.sh` ingests it (fallback).

### 5.2 Producers

Each producer is a small script that prints JSON lines to stdout; `feedctl ingest` posts
them to the feed service. Producers are deterministic and make no LLM calls.

Where they run (Claude's call): on Railway, as a second service `feed-collect` in the same
project built from the same image with start command `python -m feed.collect` and a Railway
cron schedule of `0 7,13 * * *` UTC (09:00 and 15:00 Amsterdam in winter). Collecting then does
not depend on the laptop being awake, which alongside the week of model failures is the real
cause of "research isn't constant". The laptop keeps a paused `--no-agent` Hermes job
`feed-collect` in the writer profile that runs the same command against the hosted service, as
a fallback. Creating the second Railway service is a billable resource and needs Mark's
go-ahead at that task; until then the Hermes fallback job runs unpaused.

| producer | sources | lane | notes |
|---|---|---|---|
| `producers/news.py` | existing Telegram + RSS collector, refactored to emit JSON | news | keep the current channel and feed lists; add lists to a `sources.yaml`-style plain file |
| `producers/skills.py` | ClawHub `GET /api/v1/skills?sort=trending` and `sort=createdAt`; skills.sh `/api/search?q=` for a fixed niche query list (the same public endpoint the `npx skills` CLI uses) | skill | skills.sh has no public trending/new endpoint, so the producer derives them: first-seen in the feed = new, install count up since the last run = trending. The store keeps `installs` per item per run for that. HTML scraping is out |
| `producers/repos.py` | existing GitHub lead search from `radar/skill_radar_multisource.py` | repo | watchlist stays |
| `producers/videos.py` (phase two) | Cutroom library export (`research.py`) for the seven followed creators | video | reads the local Cutroom data, no Instagram fetch |

Heuristic score per lane (recency, source weight, keyword match against Mark's niche list from
`GROWTH_SYSTEM.md`, install/star velocity for skills and repos). The score orders the menu; the
LLM only writes insights and the "why Mark" line.

### 5.3 The LinkedIn menu job

Schedule: 09:30 and 16:00 (replaces the 10:00/16:00 Editorial Radar and the 10:30 Skill Radar).

Run shape:

1. `feed-collect` has already ingested; `feed-menu` runs `feedctl menu` (8 items).
2. Hermes gets the eight items as context plus the menu prompt (`feed/prompts/menu.md`).
3. The agent does **at most one** verification fetch per item that it intends to list, drops
   items it cannot verify or that fail the "Why Mark / Why now" gate, writes one insight line
   each, and sends a Telegram message with 3–6 candidates grouped by lane. Format:

```
Research menu · Sat 25 Oct, morning

NEWS
1. Anthropic ships X — techcrunch.com/...
   Why you: you run this daily; the limit they changed is the one that bit you last week.
   Insight: the quota moved from per-day to per-hour; most coverage missed that.
2. ...

SKILLS
3. clawhub.ai/skills/foo (1.2k installs this week, new)
   Why you: fits your "is it really true" format; nobody tested the claim.
...

Reply with a number and what you want: "news post about 2", "video 3", "skip all".
```

4. If fewer than three items pass, the agent sends what it has. It never sends `[SILENT]`
   unless the feed is empty; an empty menu is itself a signal that producers broke.

The agent writes back the insight and `why` for every listed item through `feedctl set-status
shown --insight ...` so they persist for the writer and for the video phase.

### 5.4 The pick loop

Mark replies in the Hermes Telegram chat in his own words. The Hermes main agent has a skill
(`feed/SKILL.md`) that says: when the user refers to a menu item, call `feedctl pick <id> --note
"<user words>"`, then start the LinkedIn writer flow with the item's url, insight and the note
as the brief. The writer flow is unchanged from today (voice rules, anti-slop pass, visual
decision, approval before publish). When a post is published, the existing publish step calls
`feedctl set-status posted`.

Inline Telegram buttons ("Post / Video / Skip") are a possible upgrade; not in this build
because conversational picking is how Mark already works and buttons need a bot admin setup.

### 5.5 Reporting

The dashboard gets a "Feed" panel reading `/api/stats` and `/api/items`: collected per lane
today and this week, offered, shown, picked, posted, top sources by pick rate, and the last
collect time per producer so a dead producer is visible. A weekly Hermes job (Sunday 18:00)
sends the same numbers to Telegram as a `--no-agent` run of `feedctl stats`.

### 5.6 Git layout (on the `oxde` branch)

```
feed/
  README.md            what the feed is, how to run it locally and on Railway
  service.py           HTTP API + static dashboard (stdlib http.server + sqlite3)
  store.py             schema, dedupe, status transitions, stats queries
  collect.py           runs all producers and posts to the service (Railway cron entrypoint)
  feedctl.py           CLI client used by Hermes jobs
  producers/news.py skills.py repos.py
  sources.txt          channel/feed/query lists, one per line, grouped
  prompts/menu.md      the menu job prompt
  SKILL.md             Hermes skill: how to pick and hand off
  CRON.md              canonical schedules: Railway cron + Hermes jobs (replaces the old docs)
  tests/               golden tests for scoring, dedupe, menu, API
linkedin/Dockerfile    now starts feed/service.py and serves the dashboard from it
linkedin/apps/linkedin-dashboard/public/   gains the Feed panel
docs/laptop-runner-ssh.md
```

Cutover (Claude's call): the old Editorial Radar and Skill Radar Hermes jobs are disabled the
day the new jobs are registered, so Telegram traffic does not double. The old scripts and their
docs stay in Git for one proving week as a rollback, then are removed in a follow-up commit.

## 6. Decisions already made

- **One feed, lanes, two consumers.** Mark's call after discussion: a good repo or news item is
  usually both a post and a video.
- **Several candidates, not one-or-silent.** Mark's call.
- **Delivery and picking through Hermes in Telegram, conversational.** Mark's call.
- **Build thin instead of adopting Horizon.** Claude's call. Horizon (github.com/Thysrael/Horizon)
  is the strongest open-source collector, but it adds a large dependency with its own LLM
  scoring, and Hermes is already the LLM. Its source modules are a good reference and it can
  become a producer later if our collectors fall short.
- **SQLite over JSON files.** Claude's call: dedupe, status, and stats are queries.
- **Feed as a hosted service on the existing Railway project, producers on Railway cron,
  Hermes as a client.** Mark's direction ("make everything with potential to host"), Claude's
  shape. The dashboard becomes the place to read the feed and stats.
- **Stdlib HTTP server instead of a framework.** Claude's call, to match the no-new-dependency
  rule; the API is six routes. Revisit if the service ever gets a second user.
- **skills.sh trending not scraped.** Claude's call: the API requires auth and the project
  already refuses bypasses; ClawHub's open API carries most of the signal.
- **Competitor tracking and video scripts are phase two.** Mark's call.

## 7. Left to the builder

- Exact heuristic weights; tune with the golden tests and the weekly stats.
- Title-similarity method for dedupe (simple normalized-token overlap is fine).
- Prompt wording for `menu.md`, within the VOICE and anti-slop rules in the overlay.
- How the Hermes skill detects "this is a pick" versus ordinary chat.
- Telegram message splitting if a menu exceeds 4096 characters (keep numbering continuous).
- The exact Hermes cron flags, tool grants and skill registration; Claude inspects the live
  jobs over SSH before writing `feed/CRON.md` and keeps host-local IDs out of Git.

## 8. Definition of done

- The feed service is deployed to Railway service `linkedin-writer` with a `/data` volume; the
  public dashboard shows the Feed panel.
- Collection runs twice a day (Railway cron or the Hermes fallback); `/api/stats` shows items
  in three lanes with fresh collect times.
- Mark receives two menus a day for five working days with no repeated items.
- At least three picks go through to a draft via the existing writer without manual copying.
- Weekly stats message arrives once.
- Old cron jobs are disabled; their docs point to `feed/CRON.md`.

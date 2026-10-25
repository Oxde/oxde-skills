# feed — the research feed

A hosted store of research items (news, agent skills, repos) that Mark's agents collect, and a
twice-daily Telegram menu he picks from. Design: `docs/superpowers/specs/2026-10-25-research-feed-design.md`.
Schedules and host setup: `CRON.md`. Picking: `SKILL.md`. Menu job prompt: `prompts/menu.md`.

Standard library only. No dependencies to install.

```
producers/  news.py skills.py repos.py   public metadata → JSON lines (no LLM, nothing installed)
collect.py                               runs the producers and posts to the service
store.py                                 SQLite: dedupe, statuses, menus, stats
service.py                               HTTP API + serves the dashboard
feedctl.py                               CLI client used by Hermes jobs
sources.txt                              channels, feeds, queries, watchlist
```

## Run locally

```bash
FEED_ALLOW_NO_TOKEN=1 FEED_DB=/tmp/feed.db python3 -m feed.service      # http://127.0.0.1:4872
python3 -m feed.collect                                                  # fill it
python3 -m feed.feedctl menu                                             # print a menu
python3 -m feed.feedctl set-status <id> shown --insight "..." --why "..."
python3 -m feed.feedctl pick <id> --note "news post about 2"
python3 -m feed.feedctl stats
```

Tests: `python3 -m unittest discover -s feed/tests -t .`

## API

All `/api/*` routes except `/api/health` need `Authorization: Bearer $FEED_TOKEN`.

| route | method | purpose |
|---|---|---|
| `/api/health` | GET | `{"ok": true, "items": n}` |
| `/api/ingest` | POST | `{"items": [...]}` or JSON lines → counts; also expires stale items |
| `/api/menu?quota=news=4,skill=2,repo=2` | GET | unseen top items per lane; marks them `offered` |
| `/api/items?status=&lane=&since=&limit=` | GET | list |
| `/api/items/{id}` | PATCH | `status`, `insight`, `why`, `pick_note` |
| `/api/stats?days=7` | GET | per-lane counts, sources by pick rate, last collect per producer |

Statuses: `new → offered → shown → picked → drafted → posted`, plus `skipped` and `expired`.

## Deploy (Railway, project `linkedin_agent`, service `linkedin-writer`)

From the laptop, with the project token in the writer profile env (never commit or print it):

```bash
cd ~/AI-Agent-Media-Business/oxde-skills && git pull
set -a; . ~/.hermes/profiles/writer/.env; set +a
export RAILWAY_TOKEN="$linkedin_railway_token"
railway variables --service linkedin-writer --set "FEED_TOKEN=$FEED_TOKEN" --set FEED_DB=/data/feed.db
bash feed/deploy.sh          # stages Dockerfile + feed/ + public/ and runs `railway up`
curl -s "$FEED_URL/api/health"
```

The service needs a volume mounted at `/data` (created once through the API on 2026-10-25). The
service has no root directory set on Railway, so the upload root is the build root; that is why
`deploy.sh` stages a directory with the Dockerfile at its top.

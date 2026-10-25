# Research Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One hosted feed of research items (news, skills, repos) that Hermes turns into a twice-daily Telegram menu Mark picks from.

**Architecture:** A stdlib Python package `feed/` with a SQLite store behind a six-route HTTP service that also serves the existing dashboard; deterministic producer scripts post JSON lines into it; `feedctl` is the thin client Hermes jobs call. Deployed to the existing Railway service from the laptop; Hermes jobs in the `writer` profile call the hosted API.

**Tech Stack:** Python 3.12 standard library only (`sqlite3`, `http.server`, `urllib`, `unittest`), Railway (Dockerfile), Hermes Agent cron.

**Spec:** `docs/superpowers/specs/2026-10-25-research-feed-design.md`

## Global Constraints

- Python standard library only; no new dependencies. Tests are `unittest`, run with `python3 -m unittest discover -s feed/tests -v`.
- No secrets, cookies, Hermes job IDs, or Railway tokens in Git. `FEED_TOKEN`, `FEED_URL`, `FEED_DB` come from the environment.
- Never auto-publish, install, or execute scouted skills or repos. Producers fetch public metadata only.
- Status vocabulary, exactly: `new`, `offered`, `shown`, `picked`, `drafted`, `posted`, `skipped`, `expired`. Lanes: `news`, `skill`, `repo`, `post`, `video`.
- Default menu quota `news=4,skill=2,repo=2`; offered-but-not-shown items are eligible for two more menus; items older than 14 days in `new`/`offered`/`shown` expire; title dedupe window 7 days within a lane.
- Commits need Mark's explicit OK (his global rule). Each task ends with the diff staged and summarized, not committed.
- Deploys run on the laptop over `ssh hermes-mac` with the token sourced from the writer profile env; the token is never printed or copied.

## Review Focus

1. A producer that throws (network down, HTML changed) must not stop the other producers; `collect` reports it and exits non-zero only when every producer failed. Test in Task 6.
2. The same article arriving from two sources (Telegram repost of a TechCrunch link, or `http` vs `https`, trailing slash, `utm_` params) must be one item. Test in Task 1 (canonical URL) and Task 1 (title similarity).
3. A menu request when the feed is empty must return an empty menu with HTTP 200, and `run_menu.sh` must print a stable string so Hermes monitor mode suppresses the agent. Test in Tasks 2 and 7.
4. A wrong or missing bearer token must get 401 on every `/api/*` route while `/` and static files stay public. Test in Task 3.
5. Concurrent ingest and menu calls (Railway cron and Hermes firing close together) must not corrupt the store: SQLite in WAL mode, one connection per request, `BEGIN IMMEDIATE` on writes. Test in Task 3 with two threads.

---

### Task 1: Store schema, canonical IDs, ingest with dedupe, expiry

**Files:**
- Create: `feed/__init__.py` (empty), `feed/store.py`
- Test: `feed/tests/__init__.py` (empty), `feed/tests/test_store.py`

**Interfaces:**
- Produces: `canonical_url(url: str) -> str` (lowercase scheme+host, strip fragment, strip `utm_*`/`ref`/`fbclid` params, strip trailing slash, `http`→`https`).
- Produces: `item_id(url: str) -> str` = first 16 hex of sha1 of the canonical URL.
- Produces: `title_key(title: str) -> frozenset[str]` (lowercase word tokens ≥3 chars, stopwords removed) and `similar(a: frozenset, b: frozenset) -> bool` (Jaccard ≥ 0.8).
- Produces: `class Store(path: str)` with `ingest(items: list[dict], now: datetime | None = None) -> dict` returning `{"inserted": n, "duplicates": n, "rejected": n}` and `expire(now: datetime | None = None) -> int`.
- Item dict schema accepted by `ingest` (all producers emit this): `{"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}`; `metrics` is a dict; `published_at` ISO or null; missing `title` or `url` → rejected. `owner` defaults to `"oxde"`.
- Table `items` columns exactly as the spec table plus `metrics TEXT` (JSON) and `why TEXT`; `metrics` ingest merges per-run counts under the ISO date key, e.g. `{"2026-10-25": {"installs": 120}}`, so a re-ingested existing item updates `metrics` and `score` but keeps `status` and timestamps.

- [ ] **Step 1: Write the failing tests** in `feed/tests/test_store.py` (`unittest`, temp dir per test):

```python
def test_canonical_url_strips_tracking_and_normalizes(self):
    self.assertEqual(canonical_url("HTTP://TechCrunch.com/a/?utm_source=x&id=2#top"), "https://techcrunch.com/a/?id=2")
    self.assertEqual(item_id("https://techcrunch.com/a/"), item_id("http://techcrunch.com/a"))

def test_ingest_inserts_once_and_counts_duplicates(self):
    r1 = store.ingest([NEWS_ITEM]); r2 = store.ingest([NEWS_ITEM])
    self.assertEqual((r1["inserted"], r2["inserted"], r2["duplicates"]), (1, 0, 1))

def test_ingest_rejects_missing_url_or_title(self):
    self.assertEqual(store.ingest([{"lane": "news", "title": "x"}])["rejected"], 1)

def test_similar_title_same_lane_within_7_days_is_duplicate(self):
    store.ingest([NEWS_ITEM]); r = store.ingest([{**NEWS_ITEM, "url": "https://other.site/post", "title": NEWS_ITEM["title"] + "!"}])
    self.assertEqual(r["duplicates"], 1)

def test_similar_title_in_other_lane_is_not_duplicate(self): ...
def test_reingest_merges_metrics_keeps_status(self):
    store.ingest([SKILL_ITEM]); store.update(SKILL_ITEM_ID, status="shown")
    store.ingest([{**SKILL_ITEM, "metrics": {"installs": 200}}], now=TOMORROW)
    item = store.get(SKILL_ITEM_ID)
    self.assertEqual(item["status"], "shown"); self.assertEqual(set(json.loads(item["metrics"])), {TODAY_STR, TOMORROW_STR})

def test_expire_marks_old_new_offered_shown(self):
    store.ingest([NEWS_ITEM], now=NOW - timedelta(days=15)); self.assertEqual(store.expire(now=NOW), 1)
    self.assertEqual(store.get(NEWS_ID)["status"], "expired")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest feed.tests.test_store -v`
Expected: FAIL with `ModuleNotFoundError: feed.store`

- [ ] **Step 3: Implement `feed/store.py`**: `canonical_url`, `item_id`, `title_key`, `similar`, `Store.__init__` (creates schema, `PRAGMA journal_mode=WAL`), `Store.ingest`, `Store.get(id) -> dict | None`, `Store.update(id, **fields) -> dict` (used by the test; full semantics in Task 2), `Store.expire`. One `sqlite3.connect` per public method, `BEGIN IMMEDIATE` for writes. `collected_at` set from `now`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest feed.tests.test_store -v`
Expected: all PASS

- [ ] **Step 5: Stage and summarize** `git add feed/ && git --no-pager diff --cached --stat`

---

### Task 2: Menu with per-lane quota, status transitions, listing, stats

**Files:**
- Modify: `feed/store.py`
- Test: `feed/tests/test_store.py`

**Interfaces:**
- Consumes: Task 1 `Store`.
- Produces: `Store.menu(quota: dict[str, int], now=None) -> list[dict]`: per lane, items with status `new`, or `offered` with `offer_count < 3`, ordered by `score DESC, published_at DESC`; a lane with fewer items than its quota gives the remaining slots to the other lanes in quota order; every returned item is set to `offered`, `offer_count += 1`, `offered_at = now`. Returned dicts include every column.
- Produces: `Store.update(id, **fields)`: allowed fields `status`, `insight`, `why`, `pick_note`; `status="shown"` sets `shown_at`, `status="picked"` sets `picked_at`; unknown status → `ValueError`; unknown id → `KeyError`.
- Produces: `Store.list(status: str | None, lane: str | None, since: datetime | None, limit: int = 200) -> list[dict]`.
- Produces: `Store.stats(days: int = 7, now=None) -> dict` = `{"days", "lanes": {lane: {"collected", "offered", "shown", "picked", "posted"}}, "sources": [{"source", "collected", "picked", "pick_rate"}] sorted by pick_rate desc, "last_collected": {producer_prefix: iso}}` where producer prefix is the part of `source` before `:`.
- Adds columns `offer_count INTEGER DEFAULT 0`, `offered_at TEXT`.

- [ ] **Step 1: Write the failing tests**

```python
def test_menu_respects_quota_and_marks_offered(self):
    ingest 6 news, 3 skill, 1 repo; m = store.menu({"news": 4, "skill": 2, "repo": 2})
    self.assertEqual(Counter(i["lane"] for i in m), {"news": 5, "skill": 2, "repo": 1})   # repo short by 1 → news gets it
    self.assertTrue(all(i["status"] == "offered" for i in m))

def test_menu_orders_by_score_then_recency(self): ...
def test_offered_item_returns_at_most_three_times(self):
    for _ in range(3): store.menu({"news": 1})
    self.assertEqual(store.menu({"news": 1}), [])

def test_shown_item_never_returns(self): ...
def test_menu_on_empty_store_is_empty_list(self): ...
def test_update_status_sets_timestamps_and_rejects_unknown(self):
    with self.assertRaises(ValueError): store.update(ID, status="bogus")
    with self.assertRaises(KeyError): store.update("nope", status="shown")

def test_stats_counts_per_lane_and_source_pick_rate(self):
    2 news from "rss:techcrunch", 1 picked → sources[0] == {"source": "rss:techcrunch", "collected": 2, "picked": 1, "pick_rate": 0.5}
    self.assertIn("rss", stats["last_collected"])
```

- [ ] **Step 2: Run tests to verify they fail** — Expected: FAIL with `AttributeError: menu`
- [ ] **Step 3: Implement** `menu`, `update`, `list`, `stats` in `feed/store.py`.
- [ ] **Step 4: Run** `python3 -m unittest feed.tests.test_store -v` — Expected: all PASS
- [ ] **Step 5: Stage and summarize**

---

### Task 3: HTTP service with bearer auth and static dashboard

**Files:**
- Create: `feed/service.py`
- Test: `feed/tests/test_service.py`

**Interfaces:**
- Consumes: Task 2 `Store`.
- Produces: `make_server(store: Store, static_dir: str, token: str | None, host="0.0.0.0", port=0) -> ThreadingHTTPServer` and `main()` reading env `FEED_DB` (default `./feed.db`), `FEED_STATIC` (default `linkedin/apps/linkedin-dashboard/public` relative to repo root), `FEED_TOKEN` (required unless `FEED_ALLOW_NO_TOKEN=1`, else exit 2 with a message), `PORT` (default 4872).
- Routes, JSON in/out, `Content-Type: application/json`:
  - `POST /api/ingest` body `{"items": [...]}` or newline-delimited JSON → `200 {"inserted","duplicates","rejected"}`.
  - `GET /api/menu?quota=news=4,skill=2,repo=2` → `200 {"items": [...]}`; bad quota → 400.
  - `GET /api/items?status=&lane=&since=&limit=` → `200 {"items": [...]}`.
  - `PATCH /api/items/{id}` body subset of `{status, insight, why, pick_note}` → `200 item`; 404 unknown id; 400 bad status.
  - `GET /api/stats?days=7` → `200 stats`.
  - `GET /api/health` → `200 {"ok": true, "items": n}` (no auth, for Railway healthcheck).
  - Any other `/api/*` → 404. Auth: header `Authorization: Bearer <FEED_TOKEN>` on every `/api/*` except `/api/health`; wrong/missing → `401 {"error": "unauthorized"}`.
  - `GET /` and other paths → files from `static_dir` via `SimpleHTTPRequestHandler` semantics, no directory traversal (`..` → 404).

- [ ] **Step 1: Write the failing tests** (start server on port 0 in `setUp`, call with `urllib.request`):

```python
def test_health_is_public(self): 200 without token
def test_api_requires_bearer(self): GET /api/stats → 401 without, 401 wrong, 200 right
def test_static_root_serves_index_and_blocks_traversal(self): "/" → 200 text/html; "/../store.py" → 404
def test_ingest_menu_patch_roundtrip(self):
    POST ingest 3 items → inserted 3; GET menu quota news=2 → 2 items status offered; PATCH one status=shown insight="x" → 200 and status shown; GET items?status=shown → 1
def test_bad_quota_and_bad_status_are_400(self): ...
def test_concurrent_ingest_and_menu_do_not_corrupt(self):
    two threads × 50 calls each (ingest unique items / menu) → no exception; items count == 50 and no row has status outside the vocabulary
```

- [ ] **Step 2: Run** `python3 -m unittest feed.tests.test_service -v` — Expected: FAIL `ModuleNotFoundError`
- [ ] **Step 3: Implement `feed/service.py`** with `http.server.ThreadingHTTPServer` and a `BaseHTTPRequestHandler` subclass; one `Store` instance shared (it opens a connection per call); `quota` parser `parse_quota("news=4,skill=2") -> dict` raising `ValueError`.
- [ ] **Step 4: Run** — Expected: all PASS
- [ ] **Step 5: Stage and summarize**

---

### Task 4: Producer base and the news producer

**Files:**
- Create: `feed/producers/__init__.py` (empty), `feed/producers/common.py`, `feed/producers/news.py`, `feed/sources.txt`
- Test: `feed/tests/test_producers_news.py`, fixtures `feed/tests/fixtures/telegram_channel.html`, `feed/tests/fixtures/rss.xml`, `feed/tests/fixtures/atom.xml`

**Interfaces:**
- Produces (`common.py`): `fetch(url: str, timeout=25) -> str`, `fetch_json(url) -> dict | list`, `clean_html(s) -> str`, `parse_dt(s) -> datetime | None` (copied from the existing collector), `NICHE_KEYWORDS: dict[str, int]` (the weights from `daily_linkedin_topic_sources.py` plus `"skill": 3, "skills": 3, "clawhub": 3, "cursor": 2`), `keyword_score(text: str) -> int`, `recency_score(published: datetime | None, now) -> int` (0–20 linear over 48h), `clamp(score) -> int` to 0–100, `emit(items: Iterable[dict]) -> None` (print one JSON object per line), `read_sources(path, section) -> list[str]`.
- Produces (`sources.txt`): INI-like sections `[telegram]`, `[rss]`, `[clawhub_queries]`, `[skillssh_queries]`, `[github_queries]`, `[github_watchlist]`, one entry per line, `#` comments. Seed with the current channels, feeds, queries, and watchlist from the two existing scripts.
- Produces (`news.py`): `parse_telegram(html: str, channel: str) -> list[dict]`, `parse_rss(xml: str, feed_url: str) -> list[dict]`, `collect(now=None) -> list[dict]` reading `[telegram]` and `[rss]`, keeping items ≤30h old (undated kept), `source` = `tg:<channel>` / `rss:<host>`, `lane="news"`, `score = clamp(keyword_score*4 + recency_score)`; `main()` emits. Per-source failures are caught and written to stderr as `producer news: <source> failed: <Type>: <msg>`.

- [ ] **Step 1: Write failing tests**: `test_parse_telegram_fixture_yields_items_with_tg_source`, `test_parse_rss_and_atom_fixtures`, `test_keyword_score_counts_niche_terms` (`"OpenAI ships agent skills"` ≥ 4+4+3), `test_collect_skips_failed_source_and_reports_to_stderr` (monkeypatch `fetch` to raise for one URL), `test_items_match_ingest_schema` (keys exactly the schema set).
- [ ] **Step 2: Run** — Expected: FAIL
- [ ] **Step 3: Implement** by moving the parsing code out of `linkedin/overlays/oxde/scripts/daily_linkedin_topic_sources.py` (leave that file unchanged for the proving week).
- [ ] **Step 4: Run** — Expected: PASS
- [ ] **Step 5: Stage and summarize**

---

### Task 5: Skills and repos producers

**Files:**
- Create: `feed/producers/skills.py`, `feed/producers/repos.py`
- Test: `feed/tests/test_producers_skills.py`, `feed/tests/test_producers_repos.py`, fixtures `clawhub_trending.json`, `skillssh_search.json`, `github_search.json`

**Interfaces:**
- Consumes: Task 4 `common`.
- Produces (`skills.py`): `clawhub(sort: str, limit=30) -> list[dict]` from `https://clawhub.ai/api/v1/skills?sort=<trending|createdAt>&limit=` (`items[]` with `ownerHandle`, `slug`, `summary`, `stats{downloads,installs,stars}`, `createdAt` ms); url `https://clawhub.ai/<owner>/skills/<slug>`; `source="clawhub:<sort>"`; `metrics={"installs","downloads","stars"}`. `skillssh(query: str) -> list[dict]` from `https://skills.sh/api/search?q=&limit=20` (`skills[]` with `id`, `source`, `skillId`, `name`, `installs`); url `https://skills.sh/<id>`; `source="skillssh:<query>"`; `metrics={"installs"}`. `collect(now=None)` runs `clawhub("trending")`, `clawhub("createdAt")`, and every `[skillssh_queries]` entry; `lane="skill"`; `score = clamp(keyword_score*3 + log10(installs+1)*10 + (20 if created within 7 days))`.
- Produces (`repos.py`): `github_search(query: str, since_date: str) -> list[dict]` and `github_repo(full_name) -> dict` reusing the field cleaning in `radar/skill_radar_multisource.py`; `collect(now=None)` over `[github_queries]` and `[github_watchlist]`, `lane="repo"`, `source="github:search:<label>"` / `"github:watchlist"`, `metrics={"stars"}`, `score = clamp(keyword_score*3 + log10(stars+1)*10 + recency_score(pushed_at))`, skipping archived and forks. Honors `GH_TOKEN` env for the API header when present.

- [ ] **Step 1: Write failing tests** against fixtures: field mapping, URL construction, score monotonic in installs, `collect` tolerant of one failing source, schema keys exact.
- [ ] **Step 2: Run** — Expected: FAIL
- [ ] **Step 3: Implement** both modules.
- [ ] **Step 4: Run** — Expected: PASS
- [ ] **Step 5: Stage and summarize**

---

### Task 6: `collect` runner and `feedctl` client

**Files:**
- Create: `feed/collect.py`, `feed/feedctl.py`
- Test: `feed/tests/test_collect_and_feedctl.py`

**Interfaces:**
- Consumes: Tasks 3–5.
- Produces (`collect.py`): `run(producers: dict[str, Callable[[], list[dict]]], post: Callable[[list[dict]], dict]) -> int` that calls every producer, catches exceptions per producer, posts the union once, prints one summary line `collect: news=12 skill=20 repo=9 inserted=31 duplicates=10 rejected=0 failed=[]`, returns 0 when at least one producer succeeded and 1 when all failed. `main()` wires `news.collect`, `skills.collect`, `repos.collect` and `feedctl.post_ingest`. Expiry runs inside the service: the ingest handler calls `store.expire()` after `store.ingest()` (add that line to `service.py` in this task, with a test).
- Produces (`feedctl.py`): env `FEED_URL` (default `http://127.0.0.1:4872`), `FEED_TOKEN`. Functions `post_ingest(items) -> dict`, `get_menu(quota: str) -> list[dict]`, `patch_item(id, **fields) -> dict`, `get_stats(days) -> dict`, `render_menu(items: list[dict], now: datetime) -> str` (exact format from spec §5.3: header `Research menu · <Sat 25 Oct>, <morning|afternoon>`, lane headers `NEWS`/`SKILLS`/`REPOS`, numbered items continuing across lanes, each item as `<n>. <title> — <url>` then `   id: <id> · score <score> · <source>` and the `metrics` summary for skills/repos; empty list → exactly `Research menu: nothing new.`), `render_stats(stats) -> str`. CLI subcommands: `ingest` (stdin), `menu [--quota ...]`, `pick <id> [--note ...]` (= PATCH status=picked, pick_note), `set-status <id> <status> [--insight ...] [--why ...]`, `stats [--days N]`. Non-2xx → message to stderr with status and body, exit 1.

- [ ] **Step 1: Write failing tests**: `test_run_continues_after_one_producer_fails_and_exits_0`, `test_run_exits_1_when_all_fail`, `test_render_menu_matches_golden` (golden string in test), `test_render_menu_empty`, `test_feedctl_roundtrip_against_live_service` (start Task 3 server on port 0, set env, call `ingest`/`menu`/`pick`/`stats` through `main(argv)`), `test_feedctl_reports_http_error_with_body`.
- [ ] **Step 2: Run** — Expected: FAIL
- [ ] **Step 3: Implement** both modules; add `store.expire()` call in the service ingest handler.
- [ ] **Step 4: Run** full suite `python3 -m unittest discover -s feed/tests -v` — Expected: PASS
- [ ] **Step 5: Stage and summarize**

---

### Task 7: Hermes-facing files: menu prompt, skill, run script, cron contract, README

**Files:**
- Create: `feed/prompts/menu.md`, `feed/SKILL.md`, `feed/run_menu.sh`, `feed/run_stats.sh`, `feed/CRON.md`, `feed/README.md`
- Modify: `linkedin/overlays/oxde/cron/editorial-radar.md` (add a "Superseded by `feed/CRON.md` on 2026-10-25" banner at top), `radar/CRON.md` (same banner)
- Test: `feed/tests/test_scripts.py`

**Interfaces:**
- `run_menu.sh`: `#!/usr/bin/env bash`, `set -euo pipefail`, `cd "$(dirname "$0")/.."`, `exec python3 -m feed.feedctl menu --quota "${FEED_QUOTA:-news=4,skill=2,repo=2}"`. `run_stats.sh` likewise with `stats --days 7`.
- `prompts/menu.md`: the menu-job prompt. Must contain, verbatim: the three-question gate (`Why Mark? Why now? What could a generic AI creator not honestly write here?`), the rule "at most one verification fetch per item you intend to list", the Telegram output format from spec §5.3, the write-back instruction `python3 -m feed.feedctl set-status <id> shown --insight "<one line>" --why "<one line>"` for each listed item, and "If the menu says `nothing new`, reply exactly `[SILENT]`."
- `SKILL.md`: Hermes skill frontmatter (`name: feed`, `description`) and the pick procedure: when Mark's message refers to a menu item by number, topic, or lane, resolve it from the most recent menu in this chat, run `python3 -m feed.feedctl pick <id> --note "<Mark's words>"`, then start the `linkedin-writer` flow with the item's url, insight, why, and note as the brief; on publish, `set-status <id> posted`; on "skip", `set-status <id> skipped`.
- `CRON.md`: canonical schedules and exact `hermes -p writer cron create` commands (no job IDs): `feed-menu` `30 9,16 * * *` `--script feed/run_menu.sh --monitor-script feed/run_menu.sh --skill feed --skill linkedin-writer --skill linkedin-hooks --deliver origin --failure-deliver origin`; `feed-collect` (fallback, created `--paused`) `0 9,15 * * *` `--no-agent --script feed/run_collect.sh`; `feed-stats` `0 18 * * 0` `--no-agent --script feed/run_stats.sh`. Plus the Railway cron line for `feed-collect` (`0 7,13 * * *`) and the env contract (`FEED_URL`, `FEED_TOKEN`, `GH_TOKEN` optional). Add `feed/run_collect.sh` (`exec python3 -m feed.collect`).
- `README.md`: what the feed is, local run (`FEED_ALLOW_NO_TOKEN=1 python3 -m feed.service`, then `python3 -m feed.collect`, `python3 -m feed.feedctl menu`), Railway deploy steps (Task 8), tests command.

- [ ] **Step 1: Write failing tests**: `test_run_menu_prints_nothing_new_on_empty_service` (start service, env, run script via `subprocess`, assert stdout == `Research menu: nothing new.\n`), `test_prompt_contains_gate_and_silent_rule`, `test_skill_frontmatter_valid` (first line `---`, has `name: feed`).
- [ ] **Step 2: Run** — Expected: FAIL
- [ ] **Step 3: Write the files**
- [ ] **Step 4: Run** full suite — Expected: PASS
- [ ] **Step 5: Stage and summarize**

---

### Task 8: Dockerfile, dashboard Feed panel, Railway deploy

**Files:**
- Modify: `linkedin/Dockerfile`, `linkedin/railway.toml`, `linkedin/apps/linkedin-dashboard/public/index.html`
- Create: `linkedin/apps/linkedin-dashboard/public/feed.js`
- Test: `feed/tests/test_dashboard_assets.py`

**Interfaces:**
- Dockerfile: `COPY feed /app/feed` and `COPY apps/linkedin-dashboard/public /app/public` (build context stays `linkedin/`, so add a build step that copies `../feed` — Railway builds from repo root with `dockerfilePath`; set `[build] dockerfilePath = "linkedin/Dockerfile"` and `COPY feed /app/feed`, `COPY linkedin/apps/linkedin-dashboard/public /app/public`), `ENV FEED_STATIC=/app/public FEED_DB=/data/feed.db PORT=8080`, `CMD ["python", "-m", "feed.service"]`. `railway.toml`: `healthcheckPath = "/api/health"`.
- `feed.js`: adds a `FEED` card section to the page: token input stored in `localStorage["feed_token"]`, then renders `/api/stats?days=7` (per-lane table, top sources by pick rate, last collected per producer with a red mark when older than 24h) and `/api/items?status=offered,shown,picked&limit=30`. Keep `data.json` sections working when present; the page must not break when `data.json` is missing (404 → hide those sections).
- Deploy (run over `ssh hermes-mac`, token sourced from the writer env, never printed): `railway variables --service linkedin-writer --set FEED_TOKEN=<generated 32-hex>` (generate on the laptop, store it in the writer profile `.env` as `FEED_TOKEN` and `FEED_URL=<public dashboard URL>`), `railway volume add --mount-path /data` (**billable, ask Mark first**), `railway up --service linkedin-writer --detach` from the laptop checkout, then `curl <url>/api/health`.

- [ ] **Step 1: Write failing tests**: `test_dockerfile_starts_feed_service` (Dockerfile contains `CMD ["python", "-m", "feed.service"]` and `COPY feed`), `test_index_includes_feed_js_and_feed_card`, `test_feed_js_hides_sections_on_missing_data_json` (string check for the 404 guard).
- [ ] **Step 2: Run** — Expected: FAIL
- [ ] **Step 3: Edit the files**; verify locally: `FEED_ALLOW_NO_TOKEN=1 FEED_DB=/tmp/f.db python3 -m feed.service` then open `http://127.0.0.1:4872/` in the browser pane and confirm the Feed card renders with empty stats.
- [ ] **Step 4: Run** full suite — Expected: PASS
- [ ] **Step 5: Get Mark's OK for the volume, then deploy** per the commands above; `curl -s <url>/api/health` → `{"ok": true, ...}`.
- [ ] **Step 6: Stage and summarize**

---

### Task 9: Register Hermes jobs on the laptop and retire the old ones

**Files:** none in Git (host-local). Record the outcome in `feed/CRON.md` only as behavior, never IDs.

**Interfaces:** Consumes Task 7 scripts and Task 8 `FEED_URL`/`FEED_TOKEN` in the writer env.

- [ ] **Step 1:** `ssh hermes-mac 'cd ~/AI-Agent-Media-Business/oxde-skills && git pull'`; symlink `feed/run_menu.sh`, `feed/run_collect.sh`, `feed/run_stats.sh` into `~/.hermes/profiles/writer/scripts/`; copy `feed/SKILL.md` to `~/.hermes/profiles/writer/skills/feed/SKILL.md`.
- [ ] **Step 2:** Dry run: `ssh hermes-mac 'cd ~/AI-Agent-Media-Business/oxde-skills && set -a && . ~/.hermes/profiles/writer/.env && python3 -m feed.collect && bash feed/run_menu.sh'` — Expected: summary line with `inserted>0`, then a rendered menu.
- [ ] **Step 3:** Create the three jobs with the exact commands in `feed/CRON.md`; `hermes -p writer cron run <feed-menu id>` once; confirm the Telegram message arrives and the listed items are `shown` (`feedctl stats`).
- [ ] **Step 4:** Pause `1f990ab4df95` (Editorial Radar) and `dfbc156f55c1` (default-profile Skill Radar) with `hermes cron pause`; leave the metric collector and post digest running.
- [ ] **Step 5:** `hermes cron doctor` in the writer profile — Expected: no warnings for the three new jobs.
- [ ] **Step 6:** Stage docs if anything changed and summarize.

---

### Task 10: Proving week checklist (no code)

- [ ] Day 1–5: two menus a day arrive; `feedctl stats --days 7` shows no item `shown` twice; at least three picks reached a draft via the writer without manual copying; one `feed-stats` message arrived on Sunday.
- [ ] Then: remove `radar/skill_radar_multisource.py`, `linkedin/overlays/oxde/scripts/daily_linkedin_topic_sources.py`, and the two superseded cron docs in a follow-up commit.

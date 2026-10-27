"""Thin HTTP client and CLI for the feed service. Used by Hermes jobs and the collect runner.

Environment: FEED_URL (default http://127.0.0.1:4872), FEED_TOKEN.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlencode

from feed.store import PERFORMER_MIN_LIKES, velocity

DEFAULT_URL = "http://127.0.0.1:4872"
DEFAULT_QUOTA = "news=3,skill=2,repo=2,post=2"
LANE_TITLES = {"news": "NEWS", "skill": "SKILLS", "repo": "REPOS", "post": "POSTS", "video": "VIDEOS"}
LANE_ORDER = ("news", "skill", "repo", "post", "video")
REPLY_HINT = 'Reply with a number and what you want: "news post about 2", "video 3", "skip all".'
EMPTY_MENU = "Research menu: nothing new."


class FeedError(RuntimeError):
    pass


def _request(method: str, path: str, body: Any = None, query: dict[str, Any] | None = None) -> Any:
    base = os.environ.get("FEED_URL", DEFAULT_URL).rstrip("/")
    token = os.environ.get("FEED_TOKEN", "")
    url = base + path + (f"?{urlencode({k: v for k, v in query.items() if v is not None})}" if query else "")
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as err:
        raise FeedError(f"{method} {path} -> HTTP {err.code}: {err.read().decode('utf-8', errors='replace')[:500]}") from err
    except urllib.error.URLError as err:
        raise FeedError(f"{method} {path} -> {err.reason} (FEED_URL={base})") from err


def post_ingest(items: list[dict[str, Any]]) -> dict[str, int]:
    return _request("POST", "/api/ingest", {"items": items})


def get_menu(quota: str = DEFAULT_QUOTA) -> list[dict[str, Any]]:
    return _request("GET", "/api/menu", query={"quota": quota})["items"]


def patch_item(iid: str, **fields: Any) -> dict[str, Any]:
    return _request("PATCH", f"/api/items/{iid}", {k: v for k, v in fields.items() if v is not None})


def get_items(status: str | None = None, lane: str | None = None, limit: int = 50, order: str = "collected", exclude_kinds: str | None = None) -> list[dict[str, Any]]:
    return _request("GET", "/api/items", query={"status": status, "lane": lane, "limit": limit, "order": order, "exclude_kinds": exclude_kinds})["items"]


def _hook(text: str) -> str:
    text = " ".join((text or "").split())
    for sep in (". ", "! ", "? ", " — ", ": "):
        if sep in text[:200]:
            return text.split(sep, 1)[0] + sep.strip()
    return text[:140]


def _format_guess(text: str) -> str:
    t = text or ""
    if sum(1 for l in t.splitlines() if l.strip().startswith(("→", "-", "•", "1.", "2."))) >= 3:
        return "list"
    if any(k in t.lower() for k in ("i built", "i tried", "i ran", "my repo", "i made")):
        return "receipt"
    if any(k in t.lower() for k in ("alternative to", "instead of", " vs ")):
        return "comparison"
    return "breakdown"


def render_performers(items: list[dict[str, Any]], days: int) -> str:
    """The performers library: what earned attention in the lane, best first, with the hook, the
    format, the counters, the repo it links to, and the annotation when a desk has written one."""
    if not items:
        return "Performers: none yet."
    lines = [f"Performers · LinkedIn posts in the lane with {PERFORMER_MIN_LIKES}+ likes · last {days} days"]
    for n, item in enumerate(items, 1):
        m = _latest_metrics(item.get("metrics"))
        lines += ["", f"{n}. {m.get('author') or '?'} · {m.get('likes', 0)} likes · {m.get('comments', 0)} comments · {m.get('shares', 0)} reposts · {(item.get('published_at') or '')[:10]}"]
        lines.append(f"   hook: {_hook(item.get('summary') or item.get('title'))}")
        lines.append(f"   format: {_format_guess(item.get('summary') or '')} · id: {item['id']} · {item['url']}")
        if m.get("links"):
            lines.append(f"   links: {', '.join(m['links'][:3])}")
        if item.get("insight"):
            lines.append(f"   why: {item['insight']}")
        if item.get("why"):
            lines.append(f"   borrow: {item['why']}")
    return "\n".join(lines)


def render_videos(items: list[dict[str, Any]], days: int, now: dt.datetime | None = None) -> str:
    """The video desk's input: reels by creator, outlier first, with plays and the caption."""
    if not items:
        return "Video desk: no reels."
    now = now or dt.datetime.now().astimezone()
    lines = [f"Competitor reels · last {days} days · {now.strftime('%a')} {now.day} {now.strftime('%b')}"]
    by: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        m = _latest_metrics(item.get("metrics"))
        by.setdefault(m.get("creator") or item.get("source", "").split(":", 1)[-1], []).append(item)
    n = 0
    for creator, reels in sorted(by.items(), key=lambda kv: -max(_latest_metrics(r.get("metrics")).get("outlier", 0) or 0 for r in kv[1])):
        reels.sort(key=lambda r: -(_latest_metrics(r.get("metrics")).get("outlier", 0) or 0))
        lines += ["", f"@{creator}"]
        for item in reels:
            m = _latest_metrics(item.get("metrics"))
            n += 1
            lines.append(f"{n}. {m.get('outlier', 0)}x · {m.get('plays', 0)} plays · {m.get('likes', 0)} likes · {m.get('comments', 0)} comments · {m.get('duration', 0)}s · {(item.get('published_at') or '')[:10]}")
            lines.append(f"   id: {item['id']} · {item['url']}")
            caption = " ".join((item.get("summary") or item.get("title") or "").split())
            if caption:
                lines.append(f"   caption: {caption[:200]}{'…' if len(caption) > 200 else ''}")
            if item.get("insight"):
                lines.append(f"   note: {item['insight']}")
    return "\n".join(lines)


def render_candidates(items: list[dict[str, Any]], now: dt.datetime | None = None) -> str:
    """Score-ordered candidates for a desk job: like the menu, with summaries, without offering."""
    if not items:
        return "Skill desk: no candidates."
    now = now or dt.datetime.now().astimezone()
    lines = [f"Skill desk candidates · {now.strftime('%a')} {now.day} {now.strftime('%b')}"]
    for n, item in enumerate(items, 1):
        lines.append(f"{n}. [{item['lane']}] {item['title']} — {item['url']}")
        kind = f" · kind {item['kind']}" if item.get("kind") else ""
        lines.append(f"   id: {item['id']} · status {item['status']}{kind} · score {item.get('score', 0)} · {item.get('source', '')}{_metrics_suffix(item)}")
        summary = " ".join((item.get("summary") or "").split())
        if summary:
            lines.append(f"   summary: {summary[:220]}{'…' if len(summary) > 220 else ''}")
        if item.get("insight"):
            lines.append(f"   insight: {item['insight']}")
    return "\n".join(lines)


def render_items(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No items."
    return "\n".join(
        f"{i['id']} · {i['status']} · {i['lane']}{(' · ' + i['kind']) if i.get('kind') else ''} · {i['title']} — {i['url']}"
        + (f"\n   why: {i['why']}" if i.get("why") else "")
        for i in items
    )


def get_stats(days: int = 7) -> dict[str, Any]:
    return _request("GET", "/api/stats", query={"days": days})


# -- rendering ------------------------------------------------------------------------


def _latest_metrics(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    if not isinstance(raw, dict) or not raw:
        return {}
    # Store keeps {date: {...}}; a producer dict is flat.
    if all(isinstance(v, dict) for v in raw.values()):
        return raw[max(raw)]
    return raw


def _history(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "{}")
        except json.JSONDecodeError:
            return {}
    return raw if isinstance(raw, dict) else {}


def _metrics_suffix(item: dict[str, Any]) -> str:
    history = _history(item.get("metrics"))
    metrics = _latest_metrics(history)
    parts = [f"{key} {metrics[key]}" for key in ("installs", "stars", "plays", "points", "likes") if metrics.get(key) is not None]
    if metrics.get("outlier"):
        parts.append(f"{metrics['outlier']}x creator median")
    if metrics.get("created"):
        parts.append(f"created {metrics['created']}")
    growth = velocity(history) if history and all(isinstance(v, dict) for v in history.values()) else {}
    days = sorted(history)
    for key, delta in growth.items():
        parts.append(f"+{delta} {key} since {days[0]}")
    return (" · " + " · ".join(parts)) if parts else ""


def render_menu(items: list[dict[str, Any]], now: dt.datetime | None = None) -> str:
    if not items:
        return EMPTY_MENU
    now = now or dt.datetime.now().astimezone()
    slot = "morning" if now.hour < 13 else "afternoon"
    lines = [f"Research menu · {now.strftime('%a')} {now.day} {now.strftime('%b')}, {slot}"]
    number = 0
    for lane in LANE_ORDER:
        lane_items = [i for i in items if i.get("lane") == lane]
        if not lane_items:
            continue
        lines += ["", LANE_TITLES[lane]]
        for item in lane_items:
            number += 1
            lines.append(f"{number}. {item['title']} — {item['url']}")
            lines.append(f"   id: {item['id']} · score {item.get('score', 0)} · {item.get('source', '')}{_metrics_suffix(item)}")
            summary = " ".join((item.get("summary") or "").split())
            if summary:
                lines.append(f"   summary: {summary[:220]}{'…' if len(summary) > 220 else ''}")
    lines += ["", REPLY_HINT]
    return "\n".join(lines)


def render_stats(stats: dict[str, Any]) -> str:
    lines = [f"Feed stats · last {stats.get('days', 7)} days", ""]
    for lane, counts in stats.get("lanes", {}).items():
        if not any(counts.values()):
            continue
        lines.append(f"{lane}: " + " · ".join(f"{k} {v}" for k, v in counts.items()))
    sources = stats.get("sources") or []
    if sources:
        lines += ["", "Sources by pick rate:"]
        for src in sources[:10]:
            lines.append(f"- {src['source']} {src['picked']}/{src['collected']} ({round(src['pick_rate'] * 100)}%)")
    last = stats.get("last_collected") or {}
    if last:
        lines += ["", "Last collected:"]
        for producer, when in sorted(last.items()):
            lines.append(f"- {producer} {when[:16]}")
    return "\n".join(lines)


# -- CLI ------------------------------------------------------------------------------


def _read_stdin_items() -> list[dict[str, Any]]:
    text = sys.stdin.read().strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    if text.startswith("{") and "\n" not in text:
        payload = json.loads(text)
        return payload["items"] if "items" in payload else [payload]
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="feedctl", description="Client for the research feed service")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest", help="read JSON lines (or {items:[...]}) from stdin and post them")
    menu = sub.add_parser("menu", help="print the next menu as markdown")
    menu.add_argument("--quota", default=DEFAULT_QUOTA)
    pick = sub.add_parser("pick", help="mark an item picked")
    pick.add_argument("id")
    pick.add_argument("--note", default="")
    status = sub.add_parser("set-status", help="set status and optional insight/why")
    status.add_argument("id")
    status.add_argument("status")
    status.add_argument("--insight")
    status.add_argument("--why")
    status.add_argument("--kind", choices=["skill", "tool", "framework", "pack", "other"])
    lst = sub.add_parser("list", help="list items with their ids (default: offered, shown, picked)")
    lst.add_argument("--status", default="offered,shown,picked")
    lst.add_argument("--lane")
    lst.add_argument("--limit", type=int, default=50)
    top = sub.add_parser("top", help="score-ordered candidates for a desk job (does not offer them)")
    top.add_argument("--lanes", default="skill,repo")
    top.add_argument("--status", default="new,offered,shown")
    top.add_argument("--n", type=int, default=6)
    top.add_argument("--exclude-kinds", default="framework,other")
    top.add_argument("--skips", type=int, default=10, help="append the last N skipped items with reasons")
    vids = sub.add_parser("videos", help="competitor reels of the last N days, outlier first, for the video desk")
    vids.add_argument("--days", type=int, default=7)
    vids.add_argument("--n", type=int, default=30)
    perf = sub.add_parser("performers", help="the performers library: LinkedIn posts in the lane with real engagement")
    perf.add_argument("--days", type=int, default=30)
    perf.add_argument("--n", type=int, default=20)
    perf.add_argument("--min-likes", type=int, default=PERFORMER_MIN_LIKES)
    perf.add_argument("--new", action="store_true", help="only performers nobody has annotated yet")
    stats = sub.add_parser("stats", help="print feed stats")
    stats.add_argument("--days", type=int, default=7)
    stats.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "ingest":
            print(json.dumps(post_ingest(_read_stdin_items())))
        elif args.cmd == "menu":
            print(render_menu(get_menu(args.quota)))
        elif args.cmd == "pick":
            item = patch_item(args.id, status="picked", pick_note=args.note)
            print(f"picked {item['id']}: {item['title']}")
        elif args.cmd == "set-status":
            item = patch_item(args.id, status=args.status, insight=args.insight, why=args.why, kind=args.kind)
            print(f"{item['id']} -> {item['status']}")
        elif args.cmd == "list":
            print(render_items(get_items(args.status, args.lane, args.limit)))
        elif args.cmd == "top":
            lanes = [l.strip() for l in args.lanes.split(",") if l.strip()]
            per_lane = -(-args.n // max(1, len(lanes)))  # equal share per lane so one lane cannot crowd out the others
            merged: list[dict[str, Any]] = []
            for lane in lanes:
                merged.extend(get_items(args.status, lane, per_lane, order="score", exclude_kinds=args.exclude_kinds or None))
            merged.sort(key=lambda i: i.get("score", 0), reverse=True)
            text = render_candidates(merged[: args.n])
            if args.skips and merged:
                skipped = get_items("skipped", args.lanes, args.skips)
                if skipped:
                    text += "\n\nRecently skipped (Mark's bar; do not resurface these):\n" + "\n".join(
                        f"- {i['title']}" + (f" — {i['why']}" if i.get("why") else "") for i in skipped
                    )
            print(text)
        elif args.cmd == "videos":
            since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)).isoformat()
            items = _request("GET", "/api/items", query={"lane": "video", "status": "new,offered,shown,picked,drafted,posted", "since": since, "limit": args.n, "order": "score"})["items"]
            print(render_videos(items, args.days))
        elif args.cmd == "performers":
            items = _request("GET", "/api/performers", query={"days": args.days, "limit": args.n, "min_likes": args.min_likes})["items"]
            if args.new:
                items = [i for i in items if not i.get("insight")]
            print(render_performers(items, args.days))
        elif args.cmd == "stats":
            data = get_stats(args.days)
            print(json.dumps(data, ensure_ascii=False, indent=1) if args.json else render_stats(data))
    except FeedError as exc:
        print(f"feedctl: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

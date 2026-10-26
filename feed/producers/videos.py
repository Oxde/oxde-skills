"""Videos producer: recent Instagram reels of watched creators through Apify → `video` lane.

Each reel carries plays, likes, comments, duration, the direct video URL, and an outlier ratio
against the creator's median plays in the same pull. Needs APIFY_API_KEY; without it the
producer reports once and returns nothing, so the rest of the collect still runs.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics
import urllib.request
from typing import Any

from feed.producers import common

LANE = "video"
ACTOR = "apify~instagram-reel-scraper"
API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
PER_CREATOR = int(os.environ.get("VIDEO_RESULTS_PER_CREATOR", "5"))
MAX_AGE_DAYS = 14


def fetch_reels(usernames: list[str], per_creator: int = PER_CREATOR, timeout: int = 290) -> list[dict[str, Any]]:
    token = os.environ.get("APIFY_API_KEY") or os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_API_KEY is not set")
    body = json.dumps({"username": usernames, "resultsLimit": per_creator}).encode("utf-8")
    req = urllib.request.Request(
        API.format(actor=ACTOR) + f"?timeout={timeout}",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json", "User-Agent": common.USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout + 30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"unexpected Apify response: {str(payload)[:200]}")
    return payload


def _score(text: str, plays: int, outlier: float, published: dt.datetime | None, now: dt.datetime) -> int:
    return common.clamp(common.keyword_score(text) * 2 + math.log10(plays + 1) * 8 + min(30, outlier * 10) + common.recency_score(published, now))


def to_items(reels: list[dict[str, Any]], now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(days=MAX_AGE_DAYS)
    by_creator: dict[str, list[dict[str, Any]]] = {}
    for raw in reels:
        owner = raw.get("ownerUsername") or ""
        if owner and raw.get("url"):
            by_creator.setdefault(owner, []).append(raw)
    items: list[dict[str, Any]] = []
    for owner, rows in by_creator.items():
        plays_all = [int(r.get("videoPlayCount") or 0) for r in rows]
        median = statistics.median(plays_all) if plays_all else 0
        for raw in rows:
            published = common.parse_dt(raw.get("timestamp"))
            if published and published < cutoff and not raw.get("isPinned"):
                continue
            plays = int(raw.get("videoPlayCount") or 0)
            outlier = round(plays / median, 2) if median else 0.0
            caption = " ".join((raw.get("caption") or "").split())
            title = caption[:120] if caption else f"reel by {owner} ({raw.get('shortCode')})"
            metrics = {
                "plays": plays,
                "likes": int(raw.get("likesCount") or 0),
                "comments": int(raw.get("commentsCount") or 0),
                "duration": round(float(raw.get("videoDuration") or 0), 1),
                "outlier": outlier,
                "video_url": raw.get("videoUrl") or "",
                "creator": owner,
            }
            items.append(common.make_item(
                lane=LANE, source=f"instagram:{owner}", title=title, url=raw["url"], summary=caption,
                published=published, score=_score(f"{caption} {' '.join(raw.get('hashtags') or [])}", plays, outlier, published, now),
                metrics=metrics,
            ))
    items.sort(key=lambda i: (i["score"], i["published_at"] or ""), reverse=True)
    return items


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    creators = common.read_sources("instagram_creators")
    if not creators:
        return []
    try:
        reels = fetch_reels(creators)
    except Exception as exc:
        common.report_failure("videos", "apify:instagram-reel-scraper", exc)
        return []
    return to_items(reels, now=now)


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

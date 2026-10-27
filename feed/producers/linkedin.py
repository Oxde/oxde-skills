"""LinkedIn producer: public posts in Mark's lane through Apify (harvestapi/linkedin-post-search).

The niche-signal lane the growth doc always wanted: what is resonating on LinkedIn this week,
with likes and comments. Posts land in the `post` lane next to HN and Lobsters. Needs
APIFY_API_KEY; without it the producer reports once and returns nothing.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request
from typing import Any

from feed.producers import common

LANE = "post"
ACTOR = "harvestapi~linkedin-post-search"
API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
MAX_POSTS = int(os.environ.get("LINKEDIN_POSTS_PER_QUERY", "10"))
MIN_LIKES = 5


def fetch_posts(queries: list[str], max_posts: int = MAX_POSTS, timeout: int = 190) -> list[dict[str, Any]]:
    token = os.environ.get("APIFY_API_KEY") or os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_API_KEY is not set")
    body = json.dumps({"searchQueries": queries, "maxPosts": max_posts, "sortBy": "relevance", "postedLimit": "week", "profileScraperMode": "short"}).encode("utf-8")
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


def _score(text: str, likes: int, comments: int, published: dt.datetime | None, now: dt.datetime) -> int:
    return common.clamp(common.keyword_score(text) * 2 + math.log10(likes + 1) * 12 + math.log10(comments + 1) * 8 + common.recency_score(published, now))


def to_items(posts: list[dict[str, Any]], now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    items: list[dict[str, Any]] = []
    for raw in posts:
        url = raw.get("linkedinUrl") or raw.get("url")
        content = " ".join((raw.get("content") or "").split())
        if not url or not content:
            continue
        eng = raw.get("engagement") or {}
        likes = int(eng.get("likes") or 0)
        comments = int(eng.get("comments") or 0)
        if likes < MIN_LIKES:
            continue
        # LinkedIn rewrites every link to lnkd.in; the raw post keeps them in contentAttributes.
        text_links = [a.get("textLink") for a in (raw.get("contentAttributes") or []) if isinstance(a, dict) and a.get("textLink")]
        resolved = []
        for link in text_links[:4]:
            target = common.resolve_short_link(link) if common.is_short_link(link) else link
            if target and target.startswith("https://") and target not in resolved:
                resolved.append(target)
        if resolved:
            content = content + " links: " + " ".join(resolved)
        author = raw.get("author") or {}
        posted = raw.get("postedAt") or {}
        published = common.parse_dt(posted.get("date") if isinstance(posted, dict) else posted)
        name = author.get("name") or author.get("universalName") or "unknown"
        title = f"{name}: {content[:110]}"
        items.append(common.make_item(
            lane=LANE, source=f"linkedin:{raw.get('query') or 'search'}", title=title, url=url, summary=content,
            published=published, score=_score(content, likes, comments, published, now),
            metrics={"likes": likes, "comments": comments, "shares": int(eng.get("shares") or 0), "author": name, "author_url": author.get("linkedinUrl") or "", **({"resolved_links": resolved} if resolved else {})},
        ))
    items.sort(key=lambda i: (i["score"], i["published_at"] or ""), reverse=True)
    return items


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    queries = common.read_sources("linkedin_queries")
    if not queries:
        return []
    try:
        posts = fetch_posts(queries)
    except Exception as exc:
        common.report_failure("linkedin", "apify:linkedin-post-search", exc)
        return []
    return to_items(posts, now=now)


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

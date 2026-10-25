"""Posts producer: public discussion with votes → `post` lane. Hacker News (Algolia API) and Lobsters."""
from __future__ import annotations

import datetime as dt
import math
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlencode

from feed.producers import common

LANE = "post"
HN_API = "https://hn.algolia.com/api/v1/search_by_date"
LOBSTERS_RSS = "https://lobste.rs/t/{tag}.rss"
MAX_AGE_HOURS = 48
MIN_POINTS = 5
MIN_RELEVANCE = 3  # keyword score on the title; Algolia's fuzzy search returns off-topic stories


def _score(text: str, points: int, comments: int, published: dt.datetime | None, now: dt.datetime) -> int:
    return common.clamp(common.keyword_score(text) * 3 + math.log10(points + 1) * 12 + math.log10(comments + 1) * 6 + common.recency_score(published, now))


def hn(query: str, now: dt.datetime | None = None, hits: int = 20) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    since = int((now - dt.timedelta(hours=MAX_AGE_HOURS)).timestamp())
    url = f"{HN_API}?{urlencode({'query': query, 'tags': 'story', 'hitsPerPage': hits, 'numericFilters': f'created_at_i>{since},points>={MIN_POINTS}'})}"
    out: list[dict[str, Any]] = []
    for raw in common.fetch_json(url).get("hits", []):
        title = (raw.get("title") or "").strip()
        story_url = (raw.get("url") or "").strip() or f"https://news.ycombinator.com/item?id={raw.get('objectID')}"
        if not title or common.keyword_score(title) < MIN_RELEVANCE:
            continue
        points = int(raw.get("points") or 0)
        comments = int(raw.get("num_comments") or 0)
        published = common.parse_dt(raw.get("created_at"))
        summary = f"HN {points} points · {comments} comments · https://news.ycombinator.com/item?id={raw.get('objectID')}"
        out.append(common.make_item(
            lane=LANE, source=f"hn:{query}", title=title, url=story_url, summary=summary, published=published,
            score=_score(title, points, comments, published, now), metrics={"points": points, "comments": comments},
        ))
    return out


def lobsters(tag: str, now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=MAX_AGE_HOURS)
    root = ET.fromstring(common.fetch(LOBSTERS_RSS.format(tag=tag)))
    out: list[dict[str, Any]] = []
    for entry in root.iter("item"):
        title = common.clean_html(entry.findtext("title") or "")
        link = (entry.findtext("link") or "").strip()
        published = common.parse_dt(entry.findtext("pubDate"))
        if not title or not link or (published and published < cutoff):
            continue
        comments = (entry.findtext("comments") or "").strip()
        summary = common.clean_html(entry.findtext("description") or "")[:300]
        out.append(common.make_item(
            lane=LANE, source=f"lobsters:{tag}", title=title, url=link, summary=(summary + (f" · discussion {comments}" if comments else "")).strip(),
            published=published, score=_score(title + " " + summary, 0, 0, published, now), metrics={},
        ))
    return out


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    by_url: dict[str, dict[str, Any]] = {}
    for query in common.read_sources("hn_queries"):
        try:
            for item in hn(query, now=now):
                by_url.setdefault(item["url"], item)
        except Exception as exc:
            common.report_failure("posts", f"hn:{query}", exc)
    for tag in common.read_sources("lobsters_tags"):
        try:
            for item in lobsters(tag, now=now):
                by_url.setdefault(item["url"], item)
        except Exception as exc:
            common.report_failure("posts", f"lobsters:{tag}", exc)
    items = list(by_url.values())
    items.sort(key=lambda i: (i["score"], i["published_at"] or ""), reverse=True)
    return items


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

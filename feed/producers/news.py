"""News producer: public Telegram channel pages and AI/news RSS or Atom feeds → feed items."""
from __future__ import annotations

import datetime as dt
import html
import re
import xml.etree.ElementTree as ET
from typing import Any
from urllib.parse import urlsplit

from feed.producers import common

MAX_AGE_HOURS = 30
PER_SOURCE_LIMIT = 12
LANE = "news"


def _host(url: str) -> str:
    host = urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def parse_telegram(page: str, channel: str) -> list[dict[str, Any]]:
    blocks = re.findall(
        r'<div class="tgme_widget_message(?:\s[^"]*)?"[\s\S]*?(?=<div class="tgme_widget_message(?:\s|"|$)|<section class="tgme_channel_history|</main>)',
        page,
    )
    items: list[dict[str, Any]] = []
    for block in blocks:
        date_match = re.search(r'<time[^>]+datetime="([^"]+)"', block)
        published = common.parse_dt(date_match.group(1) if date_match else None)
        link_match = re.search(r'<a class="tgme_widget_message_date" href="([^"]+)"', block)
        post_url = html.unescape(link_match.group(1)) if link_match else f"https://t.me/s/{channel}"
        text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>([\s\S]*?)</div>', block)
        text = common.clean_html(text_match.group(1)) if text_match else ""
        if not text or len(text) < 25:
            continue
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), text[:120])
        items.append(common.make_item(lane=LANE, source=f"tg:{channel}", title=first_line[:180], url=post_url,
                                      summary=text, published=published))
    return items[-PER_SOURCE_LIMIT:]


def parse_rss(xml_text: str, feed_url: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    source = f"rss:{_host(feed_url)}"
    channel = root.find("channel")
    out: list[dict[str, Any]] = []
    if channel is not None:
        for entry in channel.findall("item")[:PER_SOURCE_LIMIT]:
            title = common.clean_html(entry.findtext("title") or "")
            link = (entry.findtext("link") or "").strip()
            if not title or not link:
                continue
            published = common.parse_dt(entry.findtext("pubDate") or entry.findtext("published") or entry.findtext("updated"))
            summary = common.clean_html(entry.findtext("description") or "")[:700]
            out.append(common.make_item(lane=LANE, source=source, title=title, url=link, summary=summary, published=published))
        return out
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("atom:entry", ns)[:PER_SOURCE_LIMIT]:
        title = common.clean_html(entry.findtext("atom:title", default="", namespaces=ns) or "")
        link_el = entry.find("atom:link", ns)
        link = link_el.attrib.get("href", "") if link_el is not None else ""
        if not title or not link:
            continue
        published = common.parse_dt(entry.findtext("atom:published", namespaces=ns) or entry.findtext("atom:updated", namespaces=ns))
        summary = common.clean_html(entry.findtext("atom:summary", default="", namespaces=ns) or "")[:700]
        out.append(common.make_item(lane=LANE, source=source, title=title, url=link, summary=summary, published=published))
    return out


def _score(item: dict[str, Any], now: dt.datetime) -> int:
    published = common.parse_dt(item["published_at"])
    return common.clamp(common.keyword_score(f"{item['title']} {item['summary']}") * 4 + common.recency_score(published, now))


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=MAX_AGE_HOURS)
    items: list[dict[str, Any]] = []
    for channel in common.read_sources("telegram"):
        try:
            items.extend(parse_telegram(common.fetch(f"https://t.me/s/{channel}"), channel))
        except Exception as exc:
            common.report_failure("news", f"tg:{channel}", exc)
    for feed_url in common.read_sources("rss"):
        try:
            items.extend(parse_rss(common.fetch(feed_url), feed_url))
        except Exception as exc:
            common.report_failure("news", f"rss:{_host(feed_url)}", exc)
    fresh = []
    for item in items:
        published = common.parse_dt(item["published_at"])
        if published is None or published >= cutoff:
            item["score"] = _score(item, now)
            fresh.append(item)
    fresh.sort(key=lambda i: (i["score"], i["published_at"] or ""), reverse=True)
    return fresh


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

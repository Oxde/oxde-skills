#!/usr/bin/env python3
"""Collect public Telegram channel posts + AI/news RSS items for the LinkedIn Writer daily digest.

Public Telegram pages are read through https://t.me/s/<channel>, so this does not
require Telegram login/API credentials. Output is intentionally plain markdown for
cron injection into the LLM summarizer.
"""

from __future__ import annotations

import datetime as dt
import email.utils
import html
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

MAX_AGE_HOURS = 30
PER_SOURCE_LIMIT = 12

TELEGRAM_CHANNELS = [
    "data_secrets",
    "ai_machinelearning_big_data",
    "human20",
    "NeuralShit",
]

RSS_FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://venturebeat.com/category/ai/feed",
    "https://www.artificialintelligence-news.com/feed/",
    "https://news.mit.edu/rss/topic/artificial-intelligence2",
]


@dataclass
class Item:
    source: str
    title: str
    url: str
    published: dt.datetime | None
    body: str = ""
    kind: str = "news"


def fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36",
            "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="ignore")


def clean_html(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</p\s*>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    text = html.unescape(fragment)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    value = html.unescape(value).strip()
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def parse_telegram_channel(channel: str) -> list[Item]:
    url = f"https://t.me/s/{channel}"
    page = fetch(url)
    blocks = re.findall(r'<div class="tgme_widget_message(?:\s[^"]*)?"[\s\S]*?(?=<div class="tgme_widget_message(?:\s|"|$)|<section class="tgme_channel_history|</main>)', page)
    items: list[Item] = []
    for block in blocks:
        date_match = re.search(r'<time[^>]+datetime="([^"]+)"', block)
        published = parse_dt(date_match.group(1) if date_match else None)

        link_match = re.search(r'<a class="tgme_widget_message_date" href="([^"]+)"', block)
        post_url = html.unescape(link_match.group(1)) if link_match else url

        text_match = re.search(r'<div class="tgme_widget_message_text[^>]*>([\s\S]*?)</div>', block)
        text = clean_html(text_match.group(1)) if text_match else ""

        # Skip service/empty/media-only posts; keep enough body for the writer to judge angle.
        if not text or len(text) < 25:
            continue

        first_line = next((line.strip() for line in text.splitlines() if line.strip()), text[:120])
        title = re.sub(r"\s+", " ", first_line)[:180]
        items.append(Item(source=f"Telegram: @{channel}", title=title, url=post_url, published=published, body=text[:1200], kind="telegram"))
    return items[-PER_SOURCE_LIMIT:]


def parse_rss(url: str) -> list[Item]:
    xml_text = fetch(url)
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    source = url
    entries = []
    if channel is not None:
        source = (channel.findtext("title") or url).strip()
        entries = channel.findall("item")
        def item_to_obj(it):
            title = clean_html(it.findtext("title") or "")
            link = (it.findtext("link") or "").strip()
            pub = parse_dt(it.findtext("pubDate") or it.findtext("published") or it.findtext("updated"))
            desc = clean_html(it.findtext("description") or "")
            return Item(source=source, title=title, url=link, published=pub, body=desc[:700], kind="news")
    else:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        source = (root.findtext("atom:title", default=url, namespaces=ns) or url).strip()
        entries = root.findall("atom:entry", ns)
        def item_to_obj(it):
            title = clean_html(it.findtext("atom:title", default="", namespaces=ns) or "")
            link_el = it.find("atom:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            pub = parse_dt(it.findtext("atom:published", namespaces=ns) or it.findtext("atom:updated", namespaces=ns))
            summary = clean_html(it.findtext("atom:summary", default="", namespaces=ns) or "")
            return Item(source=source, title=title, url=link, published=pub, body=summary[:700], kind="news")

    out = []
    for entry in entries[:PER_SOURCE_LIMIT]:
        try:
            obj = item_to_obj(entry)
            if obj.title and obj.url:
                out.append(obj)
        except Exception:
            continue
    return out


def score(item: Item) -> int:
    text = f"{item.title} {item.body}".lower()
    weights = {
        # English/global sources
        "agent": 4,
        "ai agent": 5,
        "openai": 4,
        "anthropic": 4,
        "hugging face": 4,
        "google": 2,
        "meta": 2,
        "model": 2,
        "launch": 2,
        "released": 2,
        "benchmark": 2,
        "security": 3,
        "lawsuit": 3,
        "funding": 2,
        "valuation": 2,
        "startup": 2,
        "data": 1,
        "machine learning": 2,
        "llm": 3,
        "reasoning": 2,
        "workflow": 3,
        "mcp": 3,
        "api": 2,
        # Russian Telegram sources; without these @human20/Data Secrets posts get buried.
        "ии": 3,
        "агент": 4,
        "агенты": 4,
        "модель": 2,
        "модели": 2,
        "open-source": 3,
        "опенсорс": 3,
        "кодинг": 3,
        "codex": 4,
        "claude": 4,
        "hermes": 5,
        "hugging face": 4,
        "пайплайн": 4,
        "workflow.json": 4,
        "rest api": 3,
        "spaces": 2,
        "скил": 3,
        "скилы": 3,
        "автоматизац": 3,
        "безопасност": 3,
    }
    total = 0
    for key, weight in weights.items():
        if key in text:
            total += weight
    if item.kind == "telegram":
        total += 1
    return total


def main() -> int:
    now = dt.datetime.now(dt.timezone.utc)
    cutoff = now - dt.timedelta(hours=MAX_AGE_HOURS)
    items: list[Item] = []
    failures = []

    for channel in TELEGRAM_CHANNELS:
        try:
            items.extend(parse_telegram_channel(channel))
        except Exception as exc:
            failures.append(f"Telegram @{channel}: {type(exc).__name__}: {exc}")

    for feed in RSS_FEEDS:
        try:
            items.extend(parse_rss(feed))
        except Exception as exc:
            failures.append(f"RSS {feed}: {type(exc).__name__}: {exc}")

    # Fresh-only where dates exist; keep undated Telegram/news only as fallback.
    fresh = [i for i in items if i.published and i.published >= cutoff]
    if not fresh:
        fresh = [i for i in items if i.published is None]

    # De-dupe by URL/title.
    seen = set()
    deduped = []
    for item in fresh:
        key = item.url or item.title.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    deduped.sort(key=lambda i: (score(i), i.published or dt.datetime.min.replace(tzinfo=dt.timezone.utc)), reverse=True)

    print(f"# Daily LinkedIn source scan")
    print(f"Generated: {now.isoformat()}")
    print(f"Window: last {MAX_AGE_HOURS}h")
    print(f"Sources: {', '.join('@' + c for c in TELEGRAM_CHANNELS)} + {len(RSS_FEEDS)} AI/news RSS feeds")
    print()

    if failures:
        print("## Fetch warnings")
        for failure in failures[:8]:
            print(f"- {failure}")
        print()

    if not deduped:
        print("No fresh items found.")
        return 0

    print("## Candidate items")
    for idx, item in enumerate(deduped[:24], 1):
        age = "unknown age"
        if item.published:
            hours = int((now - item.published).total_seconds() // 3600)
            age = f"{hours}h ago"
        body = re.sub(r"\s+", " ", item.body).strip()
        if len(body) > 500:
            body = body[:500].rstrip() + "…"
        print(f"{idx}. [{score(item)}] {item.title}")
        print(f"   Source: {item.source} ({age})")
        print(f"   Link: {item.url}")
        if body and body.lower() != item.title.lower():
            print(f"   Notes: {body}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

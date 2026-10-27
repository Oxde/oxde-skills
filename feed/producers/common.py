"""Shared helpers for feed producers: fetching, parsing, scoring, source lists, emitting.

Every producer emits dicts with exactly these keys:
    lane, source, title, url, summary, published_at, score, metrics
"""
from __future__ import annotations

import datetime as dt
import email.utils
import html
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any, Iterable

SOURCES_FILE = Path(__file__).resolve().parent.parent / "sources.txt"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/537.36 oxde-feed/1.0"
SCHEMA = ("lane", "source", "title", "url", "summary", "published_at", "score", "metrics")

# Weights carried over from daily_linkedin_topic_sources.py, plus skill-lane terms.
NICHE_KEYWORDS: dict[str, int] = {
    "agent": 4, "ai agent": 5, "openai": 4, "anthropic": 4, "hugging face": 4, "google": 2, "meta": 2,
    "model": 2, "launch": 2, "released": 2, "benchmark": 2, "security": 3, "lawsuit": 3, "funding": 2,
    "valuation": 2, "startup": 2, "data": 1, "machine learning": 2, "llm": 3, "reasoning": 2,
    "workflow": 3, "mcp": 3, "api": 2, "codex": 4, "claude": 4, "hermes": 5, "open-source": 3,
    "rest api": 3, "spaces": 2, "skill": 3, "skills": 3, "clawhub": 3, "cursor": 2,
    # Russian Telegram sources; without these @human20/Data Secrets posts get buried.
    "ии": 3, "агент": 4, "агенты": 4, "модель": 2, "модели": 2, "опенсорс": 3, "кодинг": 3,
    "пайплайн": 4, "скил": 3, "скилы": 3, "автоматизац": 3, "безопасност": 3,
}


def fetch(url: str, timeout: int = 25) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def fetch_json(url: str, timeout: int = 25, headers: dict[str, str] | None = None) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_html(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    value = value.strip()
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed is not None:
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError, IndexError):
        pass
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def iso(value: dt.datetime | None) -> str | None:
    return value.isoformat() if value else None


def keyword_score(text: str) -> int:
    lowered = text.lower()
    return sum(weight for key, weight in NICHE_KEYWORDS.items() if key in lowered)


def recency_score(published: dt.datetime | None, now: dt.datetime) -> int:
    """20 for right now, falling linearly to 0 at 48 hours."""
    if published is None:
        return 0
    age_h = max(0.0, (now - published).total_seconds() / 3600)
    if age_h >= 48:
        return 0
    return round(20 * (1 - age_h / 48))


def clamp(score: float) -> int:
    return int(max(0, min(100, round(score))))


def read_sources(section: str, path: Path = SOURCES_FILE) -> list[str]:
    entries: list[str] = []
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip()
            continue
        if current == section:
            entries.append(line)
    return entries


def make_item(*, lane: str, source: str, title: str, url: str, summary: str = "", published: dt.datetime | None = None,
              score: int = 0, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "lane": lane,
        "source": source,
        "title": re.sub(r"\s+", " ", title).strip()[:200],
        "url": url.strip(),
        "summary": summary.strip()[:1200],
        "published_at": iso(published),
        "score": score,
        "metrics": metrics or {},
    }


def report_failure(producer: str, source: str, exc: BaseException) -> None:
    print(f"producer {producer}: {source} failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)


def emit(items: Iterable[dict[str, Any]]) -> None:
    for item in items:
        print(json.dumps(item, ensure_ascii=False), flush=True)


_SHORT_HOSTS = ("lnkd.in", "bit.ly", "t.co", "buff.ly", "tinyurl.com")
_resolved: dict[str, str] = {}


def resolve_short_link(url: str, timeout: int = 15) -> str:
    """Follow a LinkedIn (or other) short link to its target; returns the input when it cannot."""
    if url in _resolved:
        return _resolved[url]
    target = url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            target = resp.geturl()
            if any(h in target for h in _SHORT_HOSTS):
                # lnkd.in answers 200 with an interstitial page; the real target is the
                # external_url_click link. Fall back to the first href that is not LinkedIn's own.
                body = resp.read(60000).decode("utf-8", errors="ignore")
                m = re.search(r'data-tracking-control-name="external_url_click"[^>]*href="([^"]+)"', body)
                if not m:
                    m = re.search(r'href="(https?://(?!(?:[\w.-]*\.)?(?:lnkd\.in|linkedin\.com|licdn\.com))[^"]+)"', body)
                if m:
                    target = html.unescape(m.group(1))
    except Exception:
        target = url
    _resolved[url] = target
    return target


def short_links(text_links: list[str]) -> list[str]:
    return [u for u in text_links if any(h in u for h in _SHORT_HOSTS)]

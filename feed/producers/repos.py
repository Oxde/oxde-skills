"""Repos producer: GitHub search queries and a watchlist → feed items (metadata only)."""
from __future__ import annotations

import datetime as dt
import math
import os
import urllib.error
from typing import Any
from urllib.parse import urlencode

from feed.producers import common

LANE = "repo"
DAYS_BACK = 21
RISING_DAYS = 14
SEARCH_CREATED_DAYS = 90  # plain searches return newish repos; the watchlist covers the known ones
RISING_BONUS = 15
RISING_MIN_RELEVANCE = 4  # keyword score on name + description; README matches alone do not count
PER_QUERY = 12
API = "https://api.github.com"


_token_rejected = False


def _headers(with_token: bool = True) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GH_TOKEN")
    if token and with_token and not _token_rejected:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch(url: str) -> Any:
    """GitHub GET; a 401 means GH_TOKEN is dead, so fall back to anonymous for the rest of the run."""
    global _token_rejected
    try:
        return common.fetch_json(url, headers=_headers())
    except urllib.error.HTTPError as err:
        if err.code == 401 and "Authorization" in _headers():
            _token_rejected = True
            common.report_failure("repos", "github:auth", RuntimeError("GH_TOKEN rejected (401); continuing without it"))
            return common.fetch_json(url, headers=_headers(with_token=False))
        raise


def _score(text: str, stars: int, pushed: dt.datetime | None, now: dt.datetime) -> int:
    # Lighter weights than skills: GitHub search already pre-filters by stars and recency.
    return common.clamp(common.keyword_score(text) * 2 + math.log10(stars + 1) * 8 + common.recency_score(pushed, now))


def _item(raw: dict[str, Any], source: str, now: dt.datetime) -> dict[str, Any] | None:
    if raw.get("archived") or raw.get("fork") or not raw.get("full_name") or not raw.get("html_url"):
        return None
    stars = int(raw.get("stargazers_count") or 0)
    pushed = common.parse_dt(raw.get("pushed_at"))
    license_id = (raw.get("license") or {}).get("spdx_id") or "unknown"
    topics = ", ".join(raw.get("topics") or [])
    description = " ".join((raw.get("description") or "").split())
    summary = f"{description} · license {license_id}" + (f" · topics {topics}" if topics else "")
    metrics: dict[str, Any] = {"stars": stars}
    created = common.parse_dt(raw.get("created_at"))
    if created:
        metrics["created"] = created.date().isoformat()
    return common.make_item(
        lane=LANE, source=source, title=raw["full_name"], url=raw["html_url"], summary=summary, published=pushed,
        score=_score(f"{raw['full_name']} {description} {topics}", stars, pushed, now), metrics=metrics,
    )


def github_search(label: str, query: str, *, since_date: str, now: dt.datetime | None = None, source: str | None = None, bonus: int = 0) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    url = f"{API}/search/repositories?" + urlencode({"q": f"{query} pushed:>={since_date}", "sort": "updated", "order": "desc", "per_page": PER_QUERY})
    payload = _fetch(url)
    out = []
    for raw in payload.get("items", []):
        item = _item(raw, source or f"github:search:{label}", now)
        if not item:
            continue
        if bonus and common.keyword_score(f"{raw.get('full_name', '')} {raw.get('description') or ''}") < RISING_MIN_RELEVANCE:
            continue  # rising but off-lane: a popular new repo is not a lead unless it is about agents
        item["score"] = common.clamp(item["score"] + bonus)
        out.append(item)
    return out


def github_repo(full_name: str, now: dt.datetime | None = None) -> dict[str, Any] | None:
    now = now or dt.datetime.now(dt.timezone.utc)
    return _item(_fetch(f"{API}/repos/{full_name}"), "github:watchlist", now)


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    since_date = (now - dt.timedelta(days=DAYS_BACK)).date().isoformat()
    created_floor = (now - dt.timedelta(days=SEARCH_CREATED_DAYS)).date().isoformat()
    by_url: dict[str, dict[str, Any]] = {}
    for entry in common.read_sources("github_queries"):
        label, _, query = entry.partition("|")
        label, query = label.strip(), (query or label).strip()
        try:
            for item in github_search(label, f"{query} created:>={created_floor}", since_date=since_date, now=now):
                by_url[item["url"]] = item
        except Exception as exc:
            common.report_failure("repos", f"github:search:{label}", exc)
    rising_since = (now - dt.timedelta(days=RISING_DAYS)).date().isoformat()
    for entry in common.read_sources("github_rising"):
        label, _, query = entry.partition("|")
        label, query = label.strip(), (query or label).strip()
        try:
            for item in github_search(label, f"{query} created:>={rising_since}", since_date=since_date, now=now, source=f"github:rising:{label}", bonus=RISING_BONUS):
                by_url[item["url"]] = item  # rising beats a plain search hit for the same repo
        except Exception as exc:
            common.report_failure("repos", f"github:rising:{label}", exc)
    for full_name in common.read_sources("github_watchlist"):
        try:
            item = github_repo(full_name, now=now)
            if item:
                by_url[item["url"]] = item  # watchlist wins over search for the same repo
        except Exception as exc:
            common.report_failure("repos", f"github:watchlist:{full_name}", exc)
    items = list(by_url.values())
    items.sort(key=lambda i: (i["score"], i["published_at"] or ""), reverse=True)
    return items


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

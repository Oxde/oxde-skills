"""Watched LinkedIn accounts: recent posts of creators who perform in Mark's lane, with counters,
through Apify (harvestapi/linkedin-profile-posts). Same item shape as the search producer; the
store turns the ones with real engagement into performers."""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from typing import Any

from feed.producers import common, linkedin

ACTOR = "harvestapi~linkedin-profile-posts"
API = "https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items"
MAX_POSTS = int(os.environ.get("LINKEDIN_ACCOUNT_POSTS", "10"))


def fetch_account_posts(handles: list[str], max_posts: int = MAX_POSTS, timeout: int = 230) -> list[dict[str, Any]]:
    token = os.environ.get("APIFY_API_KEY") or os.environ.get("APIFY_TOKEN")
    if not token:
        raise RuntimeError("APIFY_API_KEY is not set")
    urls = [h if h.startswith("http") else f"https://www.linkedin.com/in/{h}" for h in handles]
    body = json.dumps({"profileUrls": urls, "maxPosts": max_posts, "postedLimit": "month"}).encode("utf-8")
    req = urllib.request.Request(
        API.format(actor=ACTOR) + f"?timeout={timeout}", data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "application/json", "User-Agent": common.USER_AGENT},
    )
    with urllib.request.urlopen(req, timeout=timeout + 30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError(f"unexpected Apify response: {str(payload)[:200]}")
    return payload


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    handles = common.read_sources("linkedin_accounts")
    if not handles:
        return []
    try:
        posts = fetch_account_posts(handles)
    except Exception as exc:
        common.report_failure("linkedin_accounts", "apify:linkedin-profile-posts", exc)
        return []
    for raw in posts:
        raw.setdefault("query", "watch:" + ((raw.get("author") or {}).get("universalName") or "account"))
    items = linkedin.to_items(posts, now=now)
    for item in items:
        item["source"] = item["source"].replace("linkedin:watch:", "linkedin-watch:")
    return items


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Public metadata-only discovery collector for the Oxde Skill Radar.

It intentionally does not download, install, or execute third-party skills. It
collects leads from GitHub, ClawHub, and skills.sh for a later agent review.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request

DAYS_BACK = 21
GITHUB_QUERIES = [
    ("agent skills", "agent skills in:name,description stars:>=10"),
    ("Claude skills", "claude skills in:name,description stars:>=10"),
    ("AI agent workflows", "ai agent workflows in:name,description stars:>=20"),
]
GITHUB_WATCHLIST = ["anthropics/skills", "vercel-labs/agent-skills", "openai/skills", "obra/superpowers"]
CLAWHUB_QUERIES = ["agent", "video", "copywriting", "research"]
HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "Oxde-Skill-Radar/0.2"}


def fetch_json(url: str) -> dict:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(request, timeout=25) as response:
        return response.read().decode("utf-8", errors="replace")


def clean_repo(item: dict, source: str) -> dict:
    license_info = item.get("license") or {}
    return {
        "full_name": item.get("full_name"), "url": item.get("html_url"),
        "description": item.get("description") or "", "stars": item.get("stargazers_count") or 0,
        "pushed_at": item.get("pushed_at"), "license": license_info.get("spdx_id") or "unknown",
        "topics": item.get("topics") or [], "archived": bool(item.get("archived")),
        "fork": bool(item.get("fork")), "source": source,
    }


def github_leads() -> list[dict]:
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS_BACK)).date().isoformat()
    repos: dict[str, dict] = {}
    for label, query in GITHUB_QUERIES:
        url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode({
            "q": f"{query} pushed:>={cutoff}", "sort": "updated", "order": "desc", "per_page": 12,
        })
        try:
            for item in fetch_json(url).get("items", []):
                record = clean_repo(item, f"GitHub search: {label}")
                repos[record["full_name"]] = record
        except Exception as exc:
            print(f"- GitHub search {label} unavailable: {type(exc).__name__}")
    for repo in GITHUB_WATCHLIST:
        try:
            record = clean_repo(fetch_json(f"https://api.github.com/repos/{repo}"), "GitHub watchlist")
            repos[record["full_name"]] = record
        except Exception as exc:
            print(f"- GitHub watchlist {repo} unavailable: {type(exc).__name__}")
    return sorted((r for r in repos.values() if not r["archived"] and not r["fork"]), key=lambda r: (r["pushed_at"] or "", r["stars"]), reverse=True)


def main() -> None:
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=DAYS_BACK)).date().isoformat()
    print("# Oxde Skill Radar — discovery leads")
    print(f"Window: GitHub repositories pushed since {cutoff}")
    print("Metadata only. Nothing here is installed, executed, trusted, or endorsed.")
    print("\n## GitHub")
    for index, record in enumerate(github_leads()[:30], 1):
        description = " ".join(record["description"].split())[:260] or "—"
        print(f"{index}. {record['full_name']} — {record['stars']} stars · pushed {record['pushed_at']}")
        print(f"   URL: {record['url']}")
        print(f"   License: {record['license']} · Topics: {', '.join(record['topics'][:8]) or '—'}")
        print(f"   Source: {record['source']}\n   Description: {description}")

    print("\n## ClawHub")
    print("Registry metrics are leads, not security approval or unique-user proof.")
    for query in CLAWHUB_QUERIES:
        try:
            url = "https://clawhub.ai/api/v1/search?" + urllib.parse.urlencode({"q": query, "limit": 10})
            print(f"\n### Query: {query}")
            for item in fetch_json(url).get("results", [])[:8]:
                item = item or {}; native = (item.get("native") or {}).get("skill") or {}; stats = native.get("stats") or {}
                owner = item.get("ownerHandle") or (item.get("owner") or {}).get("handle") or "unknown"
                slug = item.get("slug") or "unknown"
                summary = " ".join((item.get("summary") or native.get("summary") or "").split())[:240]
                print(f"- {owner}/{slug} | downloads={item.get('downloads')} installs={stats.get('installs')} stars={stats.get('stars')}")
                print(f"  URL: https://clawhub.ai/{owner}/skills/{slug}\n  Summary: {summary or '—'}")
        except Exception as exc:
            print(f"\n### Query: {query}\n- unavailable: {type(exc).__name__}")

    print("\n## skills.sh")
    print("Public leaderboard links only. Pack-level installs can inflate per-skill numbers.")
    for page in ["trending", "hot"]:
        try:
            hrefs = re.findall(r'href=["\'](/[^"\'#?]+)["\']', fetch_text(f"https://www.skills.sh/{page}"))
            seen: list[str] = []
            for href in hrefs:
                parts = href.strip("/").split("/")
                if len(parts) == 3 and all(parts) and href not in seen:
                    seen.append(href)
            print(f"\n### {page}")
            for href in seen[:20]:
                print(f"- https://www.skills.sh{html.unescape(href)}")
        except Exception as exc:
            print(f"\n### {page}\n- unavailable: {type(exc).__name__}")


if __name__ == "__main__":
    main()

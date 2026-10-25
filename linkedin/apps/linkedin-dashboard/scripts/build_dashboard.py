#!/usr/bin/env python3
"""Build JSON for the local LinkedIn intelligence dashboard."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def parse_archive(index: Path) -> list[dict]:
    if not index.exists():
        return []
    posts: list[dict] = []
    current: dict | None = None
    for line in index.read_text(errors="ignore").splitlines():
        if line.startswith("## "):
            if current:
                posts.append(current)
            current = {"published_at": line[3:].strip(), "hook": "", "urn": "", "topic": ""}
        elif current and line.startswith("- Hook:"):
            current["hook"] = line.split(":", 1)[1].strip()
        elif current and "LinkedIn URN:" in line:
            match = re.search(r"`([^`]+)`", line)
            current["urn"] = match.group(1) if match else ""
        elif current and line.startswith("- Topic:"):
            current["topic"] = line.split(":", 1)[1].strip()
    if current:
        posts.append(current)
    return posts[:12]


def parse_active(active: Path) -> list[dict]:
    if not active.exists():
        return []
    items = []
    for line in active.read_text(errors="ignore").splitlines():
        match = re.match(r"\d+\. \[\[([^\]]+)\]\] — `([^`]+)`;?\s*(.*)", line)
        if match:
            items.append({"title": match.group(1), "status": match.group(2), "note": match.group(3)})
    return items


def build_data(archive: Path, active: Path) -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analytics": {
            "status": "not_connected",
            "message": "Connect LinkedIn browser read access or a paid data provider to populate followers, impressions, comments, and replies.",
            "followers": None,
            "impressions_30d": None,
            "comments_to_reply": None,
        },
        "latest_posts": parse_archive(archive / "POSTS.md"),
        "active_items": parse_active(active),
        "sources": [
            {"name": "Data Secrets", "type": "Telegram lead", "status": "active", "url": "https://t.me/s/data_secrets"},
            {"name": "Human 2.0", "type": "Telegram lead", "status": "active", "url": "https://t.me/s/human20"},
            {"name": "AI / ML / Big Data", "type": "Telegram lead", "status": "active", "url": "https://t.me/s/ai_machinelearning_big_data"},
            {"name": "TechCrunch AI", "type": "RSS", "status": "active", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
            {"name": "The Verge AI", "type": "RSS", "status": "active", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"},
            {"name": "VentureBeat AI", "type": "RSS", "status": "active", "url": "https://venturebeat.com/category/ai/feed"},
        ],
        "queues": [
            {"name": "AI News Desk", "schedule": "10:00 + 14:00 daily", "status": "active", "purpose": "One verified candidate from news leads and primary sources."},
            {"name": "Active Draft Closer", "schedule": "every 15 minutes when a draft is active", "status": "active", "purpose": "Ask for the smallest decision until draft is finished; never posts."},
            {"name": "Post Performance", "schedule": "09:00 daily", "status": "waiting for read adapter", "purpose": "Metrics, comments, reply drafts, and one learning after a recent post."},
            {"name": "Niche Feed Intelligence", "schedule": "planned", "status": "needs paid data adapter", "purpose": "Analyze AI/operator posts, hooks, visible engagement, and comment opportunities."},
            {"name": "Skills Review Desk", "schedule": "planned", "status": "planned", "purpose": "Find, test, and review agent skills/repos before writing about them."},
        ],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--archive", required=True, type=Path)
    p.add_argument("--active", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(build_data(args.archive, args.active), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Collect visible LinkedIn owner-post metrics through the local browser bridge.

The script deliberately keeps the LinkedIn session in Chrome. It stores only
post activity URNs and visible counters, never cookies or browser data.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
ACTIVITY_URL = os.environ.get(
    "LINKEDIN_ACTIVITY_URL",
    "https://www.linkedin.com/in/nikita-marfitsyn-314056295/recent-activity/all/",
)
OUT_DIR = Path(
    os.environ.get(
        "LINKEDIN_METRICS_DIR",
        "/Users/nikmarf/Projects/2ndbrain/40-projects/content/linkedin/research/own-post-metrics",
    )
)
SESSION = "linkedin-own-metrics"


def bridge_env() -> dict[str, str]:
    env = os.environ.copy()
    preferred = f"{HOME}/.local/node-current/bin:{HOME}/.npm-global/bin"
    env["PATH"] = f"{preferred}:{env.get('PATH', '')}"
    return env


def call(*args: str) -> dict:
    result = subprocess.run(
        ["opencli", *args], env=bridge_env(), text=True, capture_output=True, timeout=90
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenCLI did not return JSON: {result.stderr.strip()}") from exc
    if not payload.get("ok"):
        err = payload.get("error", {})
        raise RuntimeError(f"{err.get('code', 'OPENCLI_ERROR')}: {err.get('message', '')}")
    return payload["data"]


def cards(snapshot: str) -> list[dict]:
    starts = [m.start() for m in re.finditer(r"<div role=listitem />", snapshot)]
    found: list[dict] = []
    for index, start in enumerate(starts):
        segment = snapshot[start : starts[index + 1] if index + 1 < len(starts) else len(snapshot)]
        urn = re.search(r"/analytics/post-summary/(urn:li:activity:\d+)/", segment)
        impressions = re.search(r">([\d,]+) impressions</p>", segment)
        if not urn or not impressions:
            continue
        reactions = re.search(r">([\d,]+) reactions?</div>", segment)
        comments = re.search(r">([\d,]+) comments?</(?:div|span)>", segment)
        # LinkedIn's current page gives a stable analytics URN and counters. Text
        # can be expanded separately later; do not guess text from accessibility markup.
        found.append(
            {
                "activity_urn": urn.group(1),
                "impressions": int(impressions.group(1).replace(",", "")),
                "reactions": int(reactions.group(1).replace(",", "")) if reactions else 0,
                "comments": int(comments.group(1).replace(",", "")) if comments else 0,
            }
        )
    deduped: dict[str, dict] = {item["activity_urn"]: item for item in found}
    return list(deduped.values())


def main() -> int:
    call("browser", "open", "--session", SESSION, "--window", "background", ACTIVITY_URL)
    call("browser", "wait", "--session", SESSION, "time", "3")
    state = call("browser", "state", "--session", SESSION)
    snapshot = state.get("snapshot", "")
    rows = cards(snapshot)
    if not rows:
        raise RuntimeError("EMPTY_RESULT: no visible post metric cards found")

    now = datetime.now(timezone.utc).isoformat()
    record = {
        "checked_at": now,
        "source": "local authenticated Chrome via OpenCLI Browser Bridge",
        "profile_activity_url": ACTIVITY_URL,
        "posts": rows,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "latest.json").write_text(json.dumps(record, indent=2) + "\n")
    with (OUT_DIR / "snapshots.jsonl").open("a") as fh:
        fh.write(json.dumps(record) + "\n")
    print(json.dumps({"status": "ok", "checked_at": now, "posts": rows}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}), file=sys.stderr)
        raise SystemExit(1)

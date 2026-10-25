#!/usr/bin/env python3
"""Read-only LinkedIn draft preflight.

This is not an AI detector and does not rewrite text. It flags concrete local
writing problems so an author or agent can fix them before asking for signoff.

Usage:
  python3 quality_check.py draft.txt
  printf 'draft text' | python3 quality_check.py -
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BANNED = {
    "generic reveal": [r"\bthe real story is\b", r"\bthis is the interesting part\b"],
    "AI contrast scaffold": [
        r"\bthe weird part wasn['’]t\b",
        r"\bit['’]s not .{1,80}\bit['’]s\b",
        r"\bnot .{1,40}\.\s*not .{1,40}\.\s*",
    ],
    "faux-insight setup": [
        r"\bwhat nobody tells you\b",
        r"\bmost people get .{1,50} wrong\b",
        r"\bhere['’]s the thing\b",
    ],
    "corporate/slop": [
        r"\bleverage\b", r"\bsynergy\b", r"\becosystem\b", r"\brobust\b",
        r"\bseamless\b", r"\bgame[- ]changer\b", r"\bunlock potential\b",
    ],
    "weak closer": [r"\bthoughts\?\s*$", r"\bagree\?\s*$", r"\bwho else\?\s*$"],
}


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read().strip()
    return Path(path).read_text(encoding="utf-8").strip()


def extract_draft(text: str) -> str:
    """Accept either paste-ready text or a Markdown draft file."""
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)
    heading = r"(?:Current draft|Compact draft candidate|Draft candidate|Paste-ready draft candidate)"
    match = re.search(
        rf"(?mi)^##\s+{heading}\s*$\n(.*?)(?=^##\s|\Z)",
        text,
        flags=re.DOTALL,
    )
    return (match.group(1) if match else text).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="draft file path or - for stdin")
    args = parser.parse_args()
    text = extract_draft(read_text(args.input))
    if not text:
        print("QUALITY CHECK: empty draft")
        return 2

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'./$%-]*", text)
    first = lines[0] if lines else ""
    concrete = len(re.findall(r"\$\d|\b\d+(?:\.\d+)?%?\b|https?://|`[^`]+`", text))
    flags: list[str] = []

    if len(words) > 1300:
        flags.append(f"too long: {len(words)} words; cut aggressively unless this is a story")
    if len(first) < 12:
        flags.append("hook is too short to explain the subject")
    if not re.search(r"\$\d|\b\d+\b|[A-Z][A-Za-z0-9.+-]{2,}|`[^`]+`", first):
        flags.append("hook may be abstract: no number, named actor/product, or concrete object found")
    if concrete == 0:
        flags.append("no obvious concrete proof: add a number, named source, product, quote, or example")
    if text.count("—"):
        flags.append("contains em dash; prefer a period or comma unless the dash is genuinely necessary")

    lower = text.lower()
    for label, patterns in BANNED.items():
        for pattern in patterns:
            if re.search(pattern, lower, flags=re.IGNORECASE | re.DOTALL | re.MULTILINE):
                flags.append(f"{label}: `{pattern}`")
                break

    print("LINKEDIN QUALITY CHECK")
    print(f"words: {len(words)} | nonblank lines: {len(lines)} | concrete markers: {concrete}")
    print(f"hook: {first}")
    if flags:
        print("RESULT: REVIEW")
        for flag in flags:
            print(f"- {flag}")
    else:
        print("RESULT: PASS")
        print("- no mechanical rule violations found; still run a human fact/voice read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run every producer, post the union to the feed service, print one summary line.

Exit 0 when at least one producer succeeded and the post went through; 1 otherwise.
"""
from __future__ import annotations

import sys
from typing import Any, Callable

from feed import feedctl
from feed.producers import linkedin, news, posts, repos, skills, videos

PRODUCERS: dict[str, Callable[[], list[dict[str, Any]]]] = {
    "news": news.collect,
    "skills": skills.collect,
    "repos": repos.collect,
    "posts": posts.collect,
    "videos": videos.collect,
    "linkedin": linkedin.collect,
}


def run(producers: dict[str, Callable[[], list[dict[str, Any]]]], post: Callable[[list[dict[str, Any]]], dict[str, Any]]) -> int:
    counts: dict[str, int] = {}
    failed: list[str] = []
    items: list[dict[str, Any]] = []
    for name, producer in producers.items():
        try:
            produced = producer()
        except Exception as exc:
            print(f"producer {name} failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            failed.append(name)
            counts[name] = 0
            continue
        counts[name] = len(produced)
        items.extend(produced)
    result: dict[str, Any] = {"inserted": 0, "duplicates": 0, "rejected": 0, "expired": 0}
    post_ok = False
    if len(failed) < len(producers):
        try:
            result.update(post(items))
            post_ok = True
        except Exception as exc:
            print(f"post failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
    summary = " ".join(f"{name}={n}" for name, n in counts.items())
    print(
        f"collect: {summary} inserted={result.get('inserted', 0)} duplicates={result.get('duplicates', 0)} "
        f"rejected={result.get('rejected', 0)} expired={result.get('expired', 0)} failed=[{','.join(failed)}]",
        flush=True,
    )
    return 0 if post_ok else 1


def main() -> int:
    return run(PRODUCERS, feedctl.post_ingest)


if __name__ == "__main__":
    sys.exit(main())

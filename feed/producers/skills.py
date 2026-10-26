"""Skills producer: ClawHub trending/new and skills.sh search → feed items (metadata only)."""
from __future__ import annotations

import datetime as dt
import math
from typing import Any
from urllib.parse import urlencode

from feed.producers import common

LANE = "skill"
CLAWHUB_API = "https://clawhub.ai/api/v1/skills"
SKILLSSH_API = "https://skills.sh/api/search"
NEW_WITHIN_DAYS = 7


def score(text: str, *, installs: int, created: dt.datetime | None, now: dt.datetime) -> int:
    fresh = 20 if created is not None and (now - created).days < NEW_WITHIN_DAYS else 0
    # Installs count for at most 25 points: popularity is a signal, novelty and relevance decide.
    return common.clamp(common.keyword_score(text) * 3 + min(math.log10(installs + 1), 5) * 5 + fresh)


def _ms_to_dt(value: Any) -> dt.datetime | None:
    try:
        return dt.datetime.fromtimestamp(int(value) / 1000, tz=dt.timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def clawhub(sort: str, limit: int = 30, now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    payload = common.fetch_json(f"{CLAWHUB_API}?{urlencode({'sort': sort, 'limit': limit})}")
    items: list[dict[str, Any]] = []
    for raw in payload.get("items", []):
        owner = raw.get("ownerHandle") or (raw.get("owner") or {}).get("handle")
        slug = raw.get("slug")
        if not owner or not slug:
            continue
        stats = raw.get("stats") or {}
        installs = int(stats.get("installs") or 0)
        created = _ms_to_dt(raw.get("createdAt"))
        title = raw.get("displayName") or slug
        summary = raw.get("summary") or raw.get("description") or ""
        items.append(common.make_item(
            lane=LANE, source=f"clawhub:{sort}", title=title, url=f"https://clawhub.ai/{owner}/skills/{slug}",
            summary=summary, published=created,
            score=score(f"{title} {summary} {' '.join(raw.get('topics') or [])}", installs=installs, created=created, now=now),
            metrics={"installs": installs, "downloads": int(stats.get("downloads") or 0), "stars": int(stats.get("stars") or 0)},
        ))
    return items


def skillssh(query: str, limit: int = 20, now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    payload = common.fetch_json(f"{SKILLSSH_API}?{urlencode({'q': query, 'limit': limit})}")
    items: list[dict[str, Any]] = []
    for raw in payload.get("skills", []):
        sid = raw.get("id")
        name = raw.get("name") or raw.get("skillId")
        if not sid or not name:
            continue
        installs = int(raw.get("installs") or 0)
        title = f"{name} ({raw.get('source')})" if raw.get("source") else name
        items.append(common.make_item(
            lane=LANE, source=f"skillssh:{query}", title=title, url=f"https://skills.sh/{sid}", summary="",
            published=None, score=score(f"{name} {raw.get('source') or ''}", installs=installs, created=None, now=now),
            metrics={"installs": installs},
        ))
    return items


def collect(now: dt.datetime | None = None) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(dt.timezone.utc)
    items: list[dict[str, Any]] = []
    for sort in ("trending", "createdAt"):
        try:
            items.extend(clawhub(sort, now=now))
        except Exception as exc:
            common.report_failure("skills", f"clawhub:{sort}", exc)
    for query in common.read_sources("skillssh_queries"):
        try:
            items.extend(skillssh(query, now=now))
        except Exception as exc:
            common.report_failure("skills", f"skillssh:{query}", exc)
    items.sort(key=lambda i: i["score"], reverse=True)
    return items


def main() -> int:
    common.emit(collect())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

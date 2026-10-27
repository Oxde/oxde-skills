"""SQLite store for research feed items: canonical IDs, dedupe, status lifecycle, menus, stats.

Standard library only. One connection per public method; writes use BEGIN IMMEDIATE so a
Railway cron ingest and a Hermes menu call can overlap safely.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

LANES = ("news", "skill", "repo", "post", "video")
STATUSES = ("new", "offered", "shown", "picked", "drafted", "posted", "skipped", "expired")
EXPIRABLE = ("new", "offered", "shown")
MAX_OFFERS = 2
EXPIRE_DAYS = 14
TITLE_WINDOW_DAYS = 7
TITLE_SIMILARITY = 0.8
DEFAULT_OWNER = "oxde"
UPDATABLE = ("status", "insight", "why", "pick_note", "kind")
KINDS = ("", "skill", "tool", "framework", "pack", "other", "performer")
PERFORMER_MIN_LIKES = 200
PROVEN_BONUS = 25

_TRACKING_PARAMS = ("ref", "fbclid", "gclid", "igshid", "mc_cid", "mc_eid")
_STOPWORDS = frozenset(
    "the and for with from that this into over your you are was were has have will can not but its".split()
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT 'oxde',
    lane TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    collected_at TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    metrics TEXT NOT NULL DEFAULT '{}',
    insight TEXT NOT NULL DEFAULT '',
    why TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'new',
    offer_count INTEGER NOT NULL DEFAULT 0,
    offered_at TEXT,
    shown_at TEXT,
    picked_at TEXT,
    pick_note TEXT NOT NULL DEFAULT '',
    title_key TEXT NOT NULL DEFAULT '',
    kind TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS items_status_lane ON items(status, lane);
CREATE INDEX IF NOT EXISTS items_collected ON items(collected_at);
CREATE TABLE IF NOT EXISTS performer_links (
    link_id TEXT NOT NULL,
    post_id TEXT NOT NULL,
    likes INTEGER NOT NULL DEFAULT 0,
    author TEXT NOT NULL DEFAULT '',
    posted_at TEXT,
    PRIMARY KEY (link_id, post_id)
);
CREATE INDEX IF NOT EXISTS performer_links_link ON performer_links(link_id);
"""

_LINK_RE = re.compile(r"https?://(?:www\.)?(?:github\.com/[\w.-]+/[\w.-]+|skills\.sh/[\w./-]+|clawhub\.ai/[\w./-]+)")


def extract_links(text: str) -> list[str]:
    """Repo and skill URLs mentioned in a post: the proven-topic signal."""
    seen: list[str] = []
    for m in _LINK_RE.finditer(text or ""):
        url = m.group(0).rstrip(".,);")
        parts = url.split("/")
        if "github.com" in url:
            url = "/".join(parts[:5])  # owner/repo only
        if url not in seen:
            seen.append(url)
    return seen


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def canonical_url(url: str) -> str:
    """Normalize a URL so the same article from two sources gets one ID."""
    parts = urlsplit(url.strip())
    scheme = "https" if parts.scheme.lower() in ("http", "https", "") else parts.scheme.lower()
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in _TRACKING_PARAMS
    ]
    return urlunsplit((scheme, host, path, urlencode(query), ""))


def item_id(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def title_key(title: str) -> frozenset[str]:
    tokens = re.findall(r"[a-zа-яё0-9]+", title.lower())
    # Keep every number so "GPT-5" and "GPT-6" headlines stay distinct.
    return frozenset(t for t in tokens if (len(t) >= 3 or t.isdigit()) and t not in _STOPWORDS)


def similar(a: frozenset[str], b: frozenset[str]) -> bool:
    if not a or not b:
        return False
    return len(a & b) / len(a | b) >= TITLE_SIMILARITY


def velocity(metrics: dict[str, Any]) -> dict[str, int]:
    """Growth of each counter between the earliest and latest day in a per-day metrics history."""
    days = sorted(d for d, v in metrics.items() if isinstance(v, dict))
    if len(days) < 2:
        return {}
    first, last = metrics[days[0]], metrics[days[-1]]
    out = {}
    for key in ("stars", "installs", "downloads"):
        if isinstance(first.get(key), (int, float)) and isinstance(last.get(key), (int, float)):
            delta = int(last[key]) - int(first[key])
            if delta > 0:
                out[key] = delta
    return out


def velocity_bonus(metrics: dict[str, Any]) -> int:
    """0–30 points for growth *relative to size* since first seen: +300 stars on 100 is a signal,
    +1,000 installs on 800,000 is noise. 5% growth ≈ 10 points, 15% or more = 30."""
    days = sorted(d for d, v in metrics.items() if isinstance(v, dict))
    if len(days) < 2:
        return 0
    first = metrics[days[0]]
    best = 0.0
    for key, delta in velocity(metrics).items():
        base = max(1, int(first.get(key) or 0))
        best = max(best, delta / base)
    return int(min(30, round(best * 200)))


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


class Store:
    def __init__(self, path: str):
        self.path = path
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)
            cols = {r[1] for r in conn.execute("PRAGMA table_info(items)")}
            if "kind" not in cols:  # databases created before kind existed
                conn.execute("ALTER TABLE items ADD COLUMN kind TEXT NOT NULL DEFAULT ''")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    # -- ingest -----------------------------------------------------------------------

    def ingest(self, items: list[dict[str, Any]], now: datetime | None = None) -> dict[str, int]:
        now = now or _utcnow()
        now_iso = _iso(now)
        day_key = now.date().isoformat()
        window_start = _iso(now - timedelta(days=TITLE_WINDOW_DAYS))
        counts = {"inserted": 0, "duplicates": 0, "rejected": 0}
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                for raw in items:
                    title = (raw.get("title") or "").strip()
                    url = (raw.get("url") or "").strip()
                    lane = raw.get("lane")
                    if not title or not url or lane not in LANES or urlsplit(url).scheme.lower() not in ("http", "https"):
                        counts["rejected"] += 1
                        continue
                    iid = item_id(url)
                    metrics = dict(raw.get("metrics") or {})
                    score = int(raw.get("score") or 0)
                    kind = raw.get("kind") or ""
                    # A LinkedIn post with real engagement is a performer: a shape worth mirroring,
                    # and every repo or skill it links to is a proven topic.
                    if lane == "post" and str(raw.get("source", "")).startswith("linkedin") and int(metrics.get("likes") or 0) >= PERFORMER_MIN_LIKES:
                        kind = "performer"
                        links = extract_links(f"{raw.get('summary') or ''} {raw.get('title') or ''}")
                        if links:
                            metrics["links"] = links
                        for link in links:  # runs for new and re-ingested posts alike, so a backfill works
                            conn.execute(
                                "INSERT OR REPLACE INTO performer_links (link_id, post_id, likes, author, posted_at) VALUES (?, ?, ?, ?, ?)",
                                (item_id(link), iid, int(metrics.get("likes") or 0), str(metrics.get("author") or ""), raw.get("published_at")),
                            )
                            conn.execute(
                                "UPDATE items SET score = MIN(100, score + ?), why = CASE WHEN why = '' THEN ? ELSE why END WHERE id = ? AND lane IN ('repo', 'skill')",
                                (PROVEN_BONUS, f"proven: posted on LinkedIn by {metrics.get('author') or 'someone'} with {metrics.get('likes')} likes", item_id(link)),
                            )
                    proven = conn.execute("SELECT likes, author FROM performer_links WHERE link_id = ? ORDER BY likes DESC LIMIT 1", (iid,)).fetchone() if lane in ("repo", "skill") else None
                    if proven:
                        score = min(100, score + PROVEN_BONUS)
                    existing = conn.execute("SELECT metrics FROM items WHERE id = ?", (iid,)).fetchone()
                    if existing is not None:
                        merged = json.loads(existing["metrics"] or "{}")
                        if metrics:
                            merged[day_key] = metrics
                        conn.execute(
                            "UPDATE items SET metrics = ?, score = ?, kind = CASE WHEN kind = '' THEN ? ELSE kind END WHERE id = ?",
                            (json.dumps(merged, ensure_ascii=False), min(100, score + velocity_bonus(merged)), kind, iid),
                        )
                        counts["duplicates"] += 1
                        continue
                    tkey = title_key(title)
                    recent = conn.execute(
                        "SELECT title_key FROM items WHERE lane = ? AND collected_at >= ?",
                        (lane, window_start),
                    ).fetchall()
                    if any(similar(tkey, frozenset(json.loads(r["title_key"]))) for r in recent):
                        counts["duplicates"] += 1
                        continue
                    conn.execute(
                        """INSERT INTO items (id, owner, lane, source, title, url, summary, published_at,
                           collected_at, score, metrics, title_key, kind, why)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            iid,
                            raw.get("owner") or DEFAULT_OWNER,
                            lane,
                            raw.get("source") or "unknown",
                            title,
                            url,
                            raw.get("summary") or "",
                            raw.get("published_at"),
                            now_iso,
                            score,
                            json.dumps({day_key: metrics} if metrics else {}, ensure_ascii=False),
                            json.dumps(sorted(tkey)),
                            kind,
                            f"proven: posted on LinkedIn by {proven['author'] or 'someone'} with {proven['likes']} likes" if proven else "",
                        ),
                    )
                    counts["inserted"] += 1
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return counts

    # -- read -------------------------------------------------------------------------

    def get(self, iid: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM items WHERE id = ?", (iid,)).fetchone()
        return _row_to_dict(row) if row else None

    # -- lifecycle --------------------------------------------------------------------

    def update(self, iid: str, now: datetime | None = None, **fields: Any) -> dict[str, Any]:
        unknown = set(fields) - set(UPDATABLE)
        if unknown:
            raise ValueError(f"cannot update fields {sorted(unknown)}; allowed: {UPDATABLE}")
        status = fields.get("status")
        if status is not None and status not in STATUSES:
            raise ValueError(f"unknown status {status!r}; allowed: {STATUSES}")
        if fields.get("kind") is not None and fields["kind"] not in KINDS:
            raise ValueError(f"unknown kind {fields['kind']!r}; allowed: {KINDS}")
        now_iso = _iso(now or _utcnow())
        sets = [f"{k} = ?" for k in fields]
        values: list[Any] = [fields[k] for k in fields]
        if status == "shown":
            sets.append("shown_at = ?")
            values.append(now_iso)
        if status == "picked":
            sets.append("picked_at = ?")
            values.append(now_iso)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(f"UPDATE items SET {', '.join(sets)} WHERE id = ?", (*values, iid))
            if cur.rowcount == 0:
                conn.execute("ROLLBACK")
                raise KeyError(iid)
            conn.execute("COMMIT")
        result = self.get(iid)
        assert result is not None
        return result

    def expire(self, now: datetime | None = None) -> int:
        cutoff = _iso((now or _utcnow()) - timedelta(days=EXPIRE_DAYS))
        placeholders = ",".join("?" for _ in EXPIRABLE)
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                f"UPDATE items SET status = 'expired' WHERE status IN ({placeholders}) AND collected_at < ?",
                (*EXPIRABLE, cutoff),
            )
            conn.execute("COMMIT")
        return cur.rowcount

    # -- menu -------------------------------------------------------------------------

    def menu(self, quota: dict[str, int], now: datetime | None = None, exclude_kinds: str = "framework,other") -> list[dict[str, Any]]:
        """Top unseen items per lane; short lanes donate their slots. Marks results offered."""
        bad = [lane for lane in quota if lane not in LANES]
        if bad:
            raise ValueError(f"unknown lanes {bad}; allowed: {LANES}")
        excluded = [k.strip() for k in (exclude_kinds or "").split(",") if k.strip()]
        now = now or _utcnow()
        now_iso = _iso(now)
        chosen: list[sqlite3.Row] = []
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                pools: dict[str, list[sqlite3.Row]] = {}
                for lane in quota:
                    kind_clause = f" AND kind NOT IN ({','.join('?' for _ in excluded)})" if excluded else ""
                    pools[lane] = conn.execute(
                        f"""SELECT * FROM items
                           WHERE lane = ? AND (status = 'new' OR (status = 'offered' AND offer_count < ?)){kind_clause}
                           ORDER BY score DESC, COALESCE(published_at, '') DESC, collected_at DESC""",
                        (lane, MAX_OFFERS, *excluded),
                    ).fetchall()
                spare = 0
                for lane, want in quota.items():
                    take = pools[lane][:want]
                    spare += want - len(take)
                    chosen.extend(take)
                    pools[lane] = pools[lane][want:]
                for lane in quota:
                    if spare <= 0:
                        break
                    extra = pools[lane][:spare]
                    spare -= len(extra)
                    chosen.extend(extra)
                for row in chosen:
                    conn.execute(
                        "UPDATE items SET status = 'offered', offer_count = offer_count + 1, offered_at = ? WHERE id = ?",
                        (now_iso, row["id"]),
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        ids = [row["id"] for row in chosen]
        return [item for item in (self.get(i) for i in ids) if item is not None]

    # -- list -------------------------------------------------------------------------

    def list(
        self,
        status: str | None = None,
        lane: str | None = None,
        since: datetime | None = None,
        limit: int = 200,
        order: str = "collected",
        exclude_kinds: str | None = None,
    ) -> list[dict[str, Any]]:
        if order not in ("collected", "score"):
            raise ValueError(f"order must be collected or score, not {order!r}")
        where: list[str] = []
        params: list[Any] = []
        if status:
            statuses = [s.strip() for s in status.split(",") if s.strip()]
            where.append(f"status IN ({','.join('?' for _ in statuses)})")
            params.extend(statuses)
        if lane:
            lanes = [l.strip() for l in lane.split(",") if l.strip()]
            where.append(f"lane IN ({','.join('?' for _ in lanes)})")
            params.extend(lanes)
        if since is not None:
            where.append("collected_at >= ?")
            params.append(_iso(since))
        if exclude_kinds:
            kinds = [k.strip() for k in exclude_kinds.split(",") if k.strip()]
            where.append(f"kind NOT IN ({','.join('?' for _ in kinds)})")
            params.extend(kinds)
        sql = "SELECT * FROM items"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY score DESC, collected_at DESC LIMIT ?" if order == "score" else " ORDER BY collected_at DESC, score DESC LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    # -- performers -------------------------------------------------------------------

    def performers(self, days: int = 30, limit: int = 30, min_likes: int = PERFORMER_MIN_LIKES) -> list[dict[str, Any]]:
        """LinkedIn posts in the lane with real engagement, best first: the shapes worth mirroring."""
        since = _iso(_utcnow() - timedelta(days=days))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM items WHERE kind = 'performer' AND collected_at >= ? ORDER BY collected_at DESC LIMIT 2000",
                (since,),
            ).fetchall()
        items = [_row_to_dict(r) for r in rows]
        def likes(item: dict[str, Any]) -> int:
            hist = json.loads(item.get("metrics") or "{}")
            latest = hist[max(hist)] if hist else {}
            return int(latest.get("likes") or 0)
        items = [i for i in items if likes(i) >= min_likes]
        items.sort(key=likes, reverse=True)
        return items[:limit]

    # -- stats ------------------------------------------------------------------------

    def stats(self, days: int = 7, now: datetime | None = None) -> dict[str, Any]:
        now = now or _utcnow()
        since = _iso(now - timedelta(days=days))
        lanes = {lane: {"collected": 0, "offered": 0, "shown": 0, "picked": 0, "posted": 0} for lane in LANES}
        sources: dict[str, dict[str, Any]] = {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT lane, source, status, offered_at, shown_at, picked_at FROM items WHERE collected_at >= ?",
                (since,),
            ).fetchall()
            last_rows = conn.execute(
                "SELECT source, MAX(collected_at) AS last FROM items GROUP BY source"
            ).fetchall()
        for row in rows:
            lane_stats = lanes.setdefault(row["lane"], {"collected": 0, "offered": 0, "shown": 0, "picked": 0, "posted": 0})
            lane_stats["collected"] += 1
            if row["offered_at"]:
                lane_stats["offered"] += 1
            if row["shown_at"]:
                lane_stats["shown"] += 1
            if row["picked_at"]:
                lane_stats["picked"] += 1
            if row["status"] == "posted":
                lane_stats["posted"] += 1
            src = sources.setdefault(row["source"], {"source": row["source"], "collected": 0, "picked": 0})
            src["collected"] += 1
            if row["picked_at"]:
                src["picked"] += 1
        source_list = []
        for src in sources.values():
            src["pick_rate"] = round(src["picked"] / src["collected"], 3) if src["collected"] else 0.0
            source_list.append(src)
        source_list.sort(key=lambda s: (s["pick_rate"], s["collected"]), reverse=True)
        last_collected: dict[str, str] = {}
        for row in last_rows:
            prefix = row["source"].split(":", 1)[0]
            if row["last"] and row["last"] > last_collected.get(prefix, ""):
                last_collected[prefix] = row["last"]
        return {"days": days, "lanes": lanes, "sources": source_list, "last_collected": last_collected}

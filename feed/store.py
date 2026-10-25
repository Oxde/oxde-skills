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
MAX_OFFERS = 3
EXPIRE_DAYS = 14
TITLE_WINDOW_DAYS = 7
TITLE_SIMILARITY = 0.8
DEFAULT_OWNER = "oxde"
UPDATABLE = ("status", "insight", "why", "pick_note")

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
    title_key TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS items_status_lane ON items(status, lane);
CREATE INDEX IF NOT EXISTS items_collected ON items(collected_at);
"""


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


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


class Store:
    def __init__(self, path: str):
        self.path = path
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(SCHEMA)

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
                    metrics = raw.get("metrics") or {}
                    score = int(raw.get("score") or 0)
                    existing = conn.execute("SELECT metrics FROM items WHERE id = ?", (iid,)).fetchone()
                    if existing is not None:
                        merged = json.loads(existing["metrics"] or "{}")
                        if metrics:
                            merged[day_key] = metrics
                        conn.execute(
                            "UPDATE items SET metrics = ?, score = ? WHERE id = ?",
                            (json.dumps(merged, ensure_ascii=False), score, iid),
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
                           collected_at, score, metrics, title_key)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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

    def menu(self, quota: dict[str, int], now: datetime | None = None) -> list[dict[str, Any]]:
        """Top unseen items per lane; short lanes donate their slots. Marks results offered."""
        bad = [lane for lane in quota if lane not in LANES]
        if bad:
            raise ValueError(f"unknown lanes {bad}; allowed: {LANES}")
        now = now or _utcnow()
        now_iso = _iso(now)
        chosen: list[sqlite3.Row] = []
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                pools: dict[str, list[sqlite3.Row]] = {}
                for lane in quota:
                    pools[lane] = conn.execute(
                        """SELECT * FROM items
                           WHERE lane = ? AND (status = 'new' OR (status = 'offered' AND offer_count < ?))
                           ORDER BY score DESC, COALESCE(published_at, '') DESC, collected_at DESC""",
                        (lane, MAX_OFFERS),
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
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if status:
            statuses = [s.strip() for s in status.split(",") if s.strip()]
            where.append(f"status IN ({','.join('?' for _ in statuses)})")
            params.extend(statuses)
        if lane:
            where.append("lane = ?")
            params.append(lane)
        if since is not None:
            where.append("collected_at >= ?")
            params.append(_iso(since))
        sql = "SELECT * FROM items"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY collected_at DESC, score DESC LIMIT ?"
        params.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_dict(r) for r in rows]

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

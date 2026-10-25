"""HTTP service for the research feed: six JSON routes plus the static dashboard.

Standard library only. Run with `python3 -m feed.service`. Environment:
  FEED_DB              SQLite path (default ./feed.db)
  FEED_STATIC          directory served at / (default: the LinkedIn dashboard public dir)
  FEED_TOKEN           bearer token required on /api/* (except /api/health)
  FEED_ALLOW_NO_TOKEN  set to 1 to run without a token (local development only)
  PORT                 listen port (default 4872)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from feed.store import LANES, Store

DEFAULT_PORT = 4872
DEFAULT_STATIC = Path(__file__).resolve().parent.parent / "linkedin" / "apps" / "linkedin-dashboard" / "public"
MAX_BODY = 8 * 1024 * 1024


def parse_quota(text: str) -> dict[str, int]:
    quota: dict[str, int] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        lane, sep, count = part.partition("=")
        if not sep or lane not in LANES or not count.isdigit():
            raise ValueError(f"bad quota {part!r}; expected <lane>=<n> with lane in {LANES}")
        quota[lane] = int(count)
    if not quota:
        raise ValueError("empty quota")
    return quota


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class FeedHandler(SimpleHTTPRequestHandler):
    store: Store
    token: str | None
    server_version = "feed/1.0"

    def __init__(self, *args: Any, directory: str, **kwargs: Any):
        super().__init__(*args, directory=directory, **kwargs)

    # -- helpers ----------------------------------------------------------------------

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._json(status, {"error": message})

    def _authorized(self) -> bool:
        if self.token is None:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {self.token}"

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            raise ValueError("body too large")
        return self.rfile.read(length) if length else b""

    def _read_items(self) -> list[dict[str, Any]]:
        raw = self._read_body()
        text = raw.decode("utf-8", errors="replace").strip()
        if not text:
            return []
        if text.startswith("{") and "\n" not in text.strip():
            payload = json.loads(text)
            if isinstance(payload, dict) and "items" in payload and isinstance(payload["items"], list):
                return payload["items"]
            if isinstance(payload, dict) and "items" not in payload and "url" in payload:
                return [payload]
            raise ValueError("expected {\"items\": [...]} or newline-delimited JSON objects")
        if text.startswith("["):
            payload = json.loads(text)
            if isinstance(payload, list):
                return payload
            raise ValueError("expected a JSON array")
        items = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    raise ValueError("each line must be a JSON object")
                items.append(obj)
        return items

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter default logging
        if os.environ.get("FEED_LOG"):
            super().log_message(fmt, *args)

    # -- routing ----------------------------------------------------------------------

    def _route(self, method: str) -> bool:
        """Handle /api/* routes. Returns True when handled."""
        parts = urlsplit(self.path)
        if not parts.path.startswith("/api/"):
            return False
        query = {k: v[-1] for k, v in parse_qs(parts.query).items()}
        path = parts.path.rstrip("/")
        try:
            if path == "/api/health" and method == "GET":
                self._json(200, {"ok": True, "items": len(self.store.list(limit=1_000_000))})
                return True
            if not self._authorized():
                self._error(401, "unauthorized")
                return True
            if path == "/api/ingest" and method == "POST":
                items = self._read_items()
                counts = self.store.ingest(items)
                counts["expired"] = self.store.expire()
                self._json(200, counts)
                return True
            if path == "/api/menu" and method == "GET":
                quota = parse_quota(query.get("quota", "news=4,skill=2,repo=2"))
                self._json(200, {"items": self.store.menu(quota)})
                return True
            if path == "/api/items" and method == "GET":
                items = self.store.list(
                    status=query.get("status"),
                    lane=query.get("lane"),
                    since=_parse_since(query.get("since")),
                    limit=int(query.get("limit", "200")),
                )
                self._json(200, {"items": items})
                return True
            if path.startswith("/api/items/") and method == "PATCH":
                iid = path[len("/api/items/"):]
                fields = json.loads(self._read_body() or b"{}")
                if not isinstance(fields, dict) or not fields:
                    raise ValueError("expected a JSON object with fields to update")
                try:
                    self._json(200, self.store.update(iid, **fields))
                except KeyError:
                    self._error(404, f"unknown item {iid}")
                return True
            if path == "/api/stats" and method == "GET":
                self._json(200, self.store.stats(days=int(query.get("days", "7"))))
                return True
            self._error(404, f"no route {method} {path}")
        except (ValueError, json.JSONDecodeError) as exc:
            self._error(400, str(exc))
        except Exception as exc:  # keep the server alive, report the cause
            self._error(500, f"{type(exc).__name__}: {exc}")
        return True

    def do_GET(self) -> None:  # noqa: N802
        if self._route("GET"):
            return
        if ".." in urlsplit(self.path).path:
            self._error(404, "not found")
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not self._route("POST"):
            self._error(404, "not found")

    def do_PATCH(self) -> None:  # noqa: N802
        if not self._route("PATCH"):
            self._error(404, "not found")

    def list_directory(self, path: str):  # never list directories
        self._error(404, "not found")
        return None


def make_server(store: Store, static_dir: str, token: str | None, host: str = "0.0.0.0", port: int = 0) -> ThreadingHTTPServer:
    handler = type("BoundFeedHandler", (FeedHandler,), {"store": store, "token": token})

    def factory(*args: Any, **kwargs: Any) -> FeedHandler:
        return handler(*args, directory=static_dir, **kwargs)

    server = ThreadingHTTPServer((host, port), factory)
    server.daemon_threads = True
    return server


def main() -> int:
    token = os.environ.get("FEED_TOKEN") or None
    if token is None and os.environ.get("FEED_ALLOW_NO_TOKEN") != "1":
        print("feed.service: FEED_TOKEN is not set. Set it, or FEED_ALLOW_NO_TOKEN=1 for local use.", file=sys.stderr)
        return 2
    db = os.environ.get("FEED_DB", "./feed.db")
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    static = os.environ.get("FEED_STATIC", str(DEFAULT_STATIC))
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    server = make_server(Store(db), static, token, port=port)
    print(f"feed.service: listening on :{port}, db={db}, static={static}, auth={'on' if token else 'OFF'}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())

import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from feed.service import make_server, parse_quota
from feed.store import STATUSES, Store, item_id

TOKEN = "test-token-123"


def _item(lane, n):
    return {
        "lane": lane,
        "source": f"src:{lane}",
        "title": f"{lane} story {n} about {('alpha', 'beta', 'gamma', 'delta')[n % 4]} agents",
        "url": f"https://example.com/{lane}/{n}",
        "summary": "",
        "published_at": None,
        "score": n,
        "metrics": {},
    }


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.static = root / "public"
        self.static.mkdir()
        (self.static / "index.html").write_text("<html>dashboard</html>")
        self.store = Store(str(root / "feed.db"))
        self.server = make_server(self.store, str(self.static), TOKEN, host="127.0.0.1", port=0)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, token=TOKEN):
        data = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                return resp.status, resp.headers.get("Content-Type", ""), (json.loads(raw) if raw and "json" in resp.headers.get("Content-Type", "") else raw)
        except urllib.error.HTTPError as err:
            raw = err.read()
            return err.code, err.headers.get("Content-Type", ""), (json.loads(raw) if raw and "json" in err.headers.get("Content-Type", "") else raw)


class AuthAndStaticTest(ServiceTestCase):
    def test_health_is_public(self):
        status, _, body = self.call("GET", "/api/health", token=None)
        self.assertEqual((status, body["ok"], body["items"]), (200, True, 0))

    def test_api_requires_bearer(self):
        self.assertEqual(self.call("GET", "/api/stats", token=None)[0], 401)
        self.assertEqual(self.call("GET", "/api/stats", token="wrong")[0], 401)
        self.assertEqual(self.call("GET", "/api/stats")[0], 200)
        self.assertEqual(self.call("POST", "/api/ingest", {"items": []}, token=None)[0], 401)

    def test_static_root_serves_index_and_blocks_traversal(self):
        status, ctype, body = self.call("GET", "/", token=None)
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn(b"dashboard", body)
        self.assertEqual(self.call("GET", "/../feed.db", token=None)[0], 404)
        self.assertEqual(self.call("GET", "/missing.js", token=None)[0], 404)

    def test_unknown_api_route_is_404(self):
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)


class RoundtripTest(ServiceTestCase):
    def test_ingest_menu_patch_roundtrip(self):
        status, _, body = self.call("POST", "/api/ingest", {"items": [_item("news", i) for i in range(3)]})
        self.assertEqual((status, body["inserted"]), (200, 3))
        status, _, body = self.call("GET", "/api/menu?quota=news=2")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["items"]), 2)
        self.assertTrue(all(i["status"] == "offered" for i in body["items"]))
        iid = body["items"][0]["id"]
        status, _, body = self.call("PATCH", f"/api/items/{iid}", {"status": "shown", "insight": "x"})
        self.assertEqual((status, body["status"], body["insight"]), (200, "shown", "x"))
        status, _, body = self.call("GET", "/api/items?status=shown")
        self.assertEqual((status, len(body["items"])), (200, 1))
        status, _, body = self.call("GET", "/api/stats?days=7")
        self.assertEqual(body["lanes"]["news"]["shown"], 1)
        status, _, body = self.call("GET", "/api/items?order=score&lane=news,skill")
        self.assertEqual([i["score"] for i in body["items"]], [2, 1, 0])
        self.assertEqual(self.call("GET", "/api/items?order=bogus")[0], 400)

    def test_ingest_accepts_json_lines(self):
        lines = "\n".join(json.dumps(_item("skill", i)) for i in range(2)).encode()
        req = urllib.request.Request(self.base + "/api/ingest", data=lines, method="POST",
                                     headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/x-ndjson"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(json.loads(resp.read())["inserted"], 2)

    def test_ingest_runs_expiry(self):
        from datetime import datetime, timedelta, timezone

        self.store.ingest([_item("repo", 1)], now=datetime.now(timezone.utc) - timedelta(days=20))
        self.call("POST", "/api/ingest", {"items": []})
        self.assertEqual(self.store.get(item_id("https://example.com/repo/1"))["status"], "expired")

    def test_bad_quota_and_bad_status_are_400(self):
        self.assertEqual(self.call("GET", "/api/menu?quota=bogus=1")[0], 400)
        self.assertEqual(self.call("GET", "/api/menu?quota=news")[0], 400)
        self.call("POST", "/api/ingest", {"items": [_item("news", 1)]})
        iid = item_id("https://example.com/news/1")
        self.assertEqual(self.call("PATCH", f"/api/items/{iid}", {"status": "bogus"})[0], 400)
        self.assertEqual(self.call("PATCH", f"/api/items/{iid}", {"title": "no"})[0], 400)
        self.assertEqual(self.call("PATCH", "/api/items/unknown", {"status": "shown"})[0], 404)
        self.assertEqual(self.call("POST", "/api/ingest", {"nope": 1})[0], 400)

    def test_concurrent_ingest_and_menu_do_not_corrupt(self):
        errors = []

        def ingest():
            for i in range(50):
                try:
                    self.call("POST", "/api/ingest", {"items": [_item("news", 100 + i)]})
                except Exception as exc:  # pragma: no cover - reported via assert
                    errors.append(exc)

        def menu():
            for _ in range(50):
                try:
                    self.call("GET", "/api/menu?quota=news=3")
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)

        threads = [threading.Thread(target=ingest), threading.Thread(target=menu)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        items = self.store.list(limit=1000)
        self.assertEqual(len(items), 50)
        self.assertTrue(all(i["status"] in STATUSES for i in items))


class QuotaParseTest(unittest.TestCase):
    def test_parse_quota(self):
        self.assertEqual(parse_quota("news=4,skill=2,repo=2"), {"news": 4, "skill": 2, "repo": 2})
        for bad in ("news", "news=x", "bogus=1", "", "news=-1"):
            with self.assertRaises(ValueError):
                parse_quota(bad)


if __name__ == "__main__":
    unittest.main()

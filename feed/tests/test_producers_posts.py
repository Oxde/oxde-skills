import io
import json
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, posts

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}
NOW = datetime(2026, 10, 26, 8, 0, tzinfo=timezone.utc)
HN = json.loads((FIX / "hn_search.json").read_text())
LOB = (FIX / "lobsters_ai.xml").read_text()


class PostsTest(unittest.TestCase):
    def test_hn_maps_fields_and_filters(self):
        with mock.patch.object(common, "fetch_json", return_value=HN) as fetched:
            items = posts.hn("agent skills", now=NOW)
        url = fetched.call_args[0][0]
        self.assertIn("query=agent+skills", url)
        self.assertIn("points%3E%3D5", url)
        self.assertEqual(len(items), 2)  # empty title and the off-topic knight dropped
        self.assertEqual(items[0]["url"], "https://example.dev/skills-registry")
        self.assertEqual(items[0]["source"], "hn:agent skills")
        self.assertEqual(items[0]["metrics"], {"points": 142, "comments": 37})
        self.assertIn("HN 142 points · 37 comments", items[0]["summary"])
        self.assertEqual(items[1]["url"], "https://news.ycombinator.com/item?id=1002")  # Ask HN has no external url
        self.assertEqual(set(items[0]), SCHEMA)
        self.assertTrue(all(i["lane"] == "post" for i in items))
        self.assertGreater(items[0]["score"], items[1]["score"] - 20)

    def test_lobsters_parses_and_drops_stale(self):
        with mock.patch.object(common, "fetch", return_value=LOB):
            items = posts.lobsters("ai", now=NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["source"], "lobsters:ai")
        self.assertEqual(items[0]["url"], "https://example.org/agent-vm")
        self.assertIn("discussion https://lobste.rs/s/abc", items[0]["summary"])
        self.assertEqual(items[0]["published_at"], "2026-10-25T10:00:00+00:00")

    def test_collect_dedupes_and_tolerates_failure(self):
        def fake_json(url, timeout=25, headers=None):
            if "hermes" in url:
                raise ConnectionError("down")
            return HN

        err = io.StringIO()
        with mock.patch.object(common, "fetch_json", side_effect=fake_json), mock.patch.object(common, "fetch", return_value=LOB), mock.patch.object(
            common, "read_sources", side_effect=lambda s: {"hn_queries": ["agent skills", "hermes agent"], "lobsters_tags": ["ai"]}[s]
        ), redirect_stderr(err):
            items = posts.collect(now=NOW)
        self.assertEqual(len(items), 3)  # 2 HN (same for both queries, deduped) + 1 lobsters
        self.assertIn("producer posts: hn:hermes agent failed: ConnectionError", err.getvalue())


if __name__ == "__main__":
    unittest.main()

import io
import json
import os
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, videos

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
REELS = json.loads((FIX / "apify_reels.json").read_text())


class VideosTest(unittest.TestCase):
    def test_to_items_maps_fields_outlier_and_drops_old_and_ownerless(self):
        items = videos.to_items(REELS, now=NOW)
        self.assertEqual({i["url"] for i in items}, {"https://www.instagram.com/p/AAA/", "https://www.instagram.com/p/BBB/", "https://www.instagram.com/p/CCC/"})
        by = {i["url"]: i for i in items}
        a = by["https://www.instagram.com/p/AAA/"]
        self.assertEqual(a["lane"], "video")
        self.assertEqual(a["source"], "instagram:nick_saraev")
        self.assertEqual(a["title"], "Comment AGENCY to build your own AI agency inside Claude Code")
        self.assertEqual(a["metrics"]["plays"], 75845)
        self.assertEqual(a["metrics"]["video_url"], "https://cdn.example/a.mp4")
        self.assertEqual(a["metrics"]["creator"], "nick_saraev")
        self.assertEqual(a["published_at"], "2026-10-25T10:00:00+00:00")
        self.assertEqual(set(a), SCHEMA)
        b = by["https://www.instagram.com/p/BBB/"]
        self.assertGreater(b["metrics"]["outlier"], 5)  # 3.4M against the creator's median (the old 1M reel is in the median too)
        self.assertEqual(items[0]["url"], b["url"])  # outlier ranks first
        c = by["https://www.instagram.com/p/CCC/"]
        self.assertEqual(c["title"], "reel by nick_saraev (CCC)")  # no caption

    def test_collect_without_key_reports_and_returns_nothing(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"APIFY_API_KEY": "", "APIFY_TOKEN": ""}), mock.patch.object(common, "read_sources", return_value=["nick_saraev"]), redirect_stderr(err):
            self.assertEqual(videos.collect(now=NOW), [])
        self.assertIn("producer videos: apify:instagram-reel-scraper failed: RuntimeError: APIFY_API_KEY is not set", err.getvalue())

    def test_collect_calls_apify_with_creators(self):
        with mock.patch.object(videos, "fetch_reels", return_value=REELS) as fetched, mock.patch.object(common, "read_sources", return_value=["nick_saraev", "chase.h.ai"]):
            items = videos.collect(now=NOW)
        self.assertEqual(fetched.call_args[0][0], ["nick_saraev", "chase.h.ai"])
        self.assertEqual(len(items), 3)


if __name__ == "__main__":
    unittest.main()

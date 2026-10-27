import io
import json
import os
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, linkedin

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}
NOW = datetime(2026, 10, 26, 15, 0, tzinfo=timezone.utc)
POSTS = json.loads((FIX / "apify_linkedin.json").read_text())


class LinkedinTest(unittest.TestCase):
    def test_to_items_maps_fields_and_filters_noise(self):
        items = linkedin.to_items(POSTS, now=NOW)
        self.assertEqual(len(items), 2)  # zero-like post and url-less post dropped
        by = {i["url"]: i for i in items}
        gta = by["https://www.linkedin.com/posts/yrebryk_gta-activity-1"]
        self.assertEqual(gta["lane"], "post")
        self.assertEqual(gta["source"], "linkedin:Claude Code agents")
        self.assertTrue(gta["title"].startswith("Yurii Rebryk: Someone used Claude Code"))
        self.assertEqual(gta["metrics"]["likes"], 2215)
        self.assertEqual(gta["metrics"]["author_url"], "https://www.linkedin.com/in/yrebryk")
        self.assertEqual(gta["published_at"], "2026-10-22T10:00:00+00:00")
        self.assertEqual(set(gta), SCHEMA)
        # Fresh and on-topic (Anthropic, agent skills, posted today) outranks older with more likes.
        self.assertEqual(items[0]["url"], "https://www.linkedin.com/posts/acolombiadev_skills-activity-2")

    def test_short_links_are_resolved_and_appended(self):
        with mock.patch.object(common, "resolve_short_link", return_value="https://github.com/anthropics/skills") as res:
            items = linkedin.to_items(POSTS, now=NOW)
        res.assert_called_once_with("https://lnkd.in/abc123")
        skills = [i for i in items if "acolombiadev" in i["url"]][0]
        self.assertTrue(skills["summary"].endswith("links: https://github.com/anthropics/skills"))
        self.assertEqual(skills["metrics"]["resolved_links"], ["https://github.com/anthropics/skills"])

    def test_collect_without_key_reports_and_returns_nothing(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"APIFY_API_KEY": "", "APIFY_TOKEN": ""}), mock.patch.object(common, "read_sources", return_value=["agent skills"]), redirect_stderr(err):
            self.assertEqual(linkedin.collect(now=NOW), [])
        self.assertIn("producer linkedin: apify:linkedin-post-search failed: RuntimeError: APIFY_API_KEY is not set", err.getvalue())

    def test_collect_passes_queries(self):
        with mock.patch.object(linkedin, "fetch_posts", return_value=POSTS) as fetched, mock.patch.object(common, "read_sources", return_value=["Claude Code agents", "agent skills"]):
            items = linkedin.collect(now=NOW)
        self.assertEqual(fetched.call_args[0][0], ["Claude Code agents", "agent skills"])
        self.assertEqual(len(items), 2)


if __name__ == "__main__":
    unittest.main()

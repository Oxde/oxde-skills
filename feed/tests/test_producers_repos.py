import io
import json
import os
import urllib.error
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, repos

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
SEARCH = json.loads((FIX / "github_search.json").read_text())


class GithubTest(unittest.TestCase):
    def setUp(self):
        repos._token_rejected = False  # module state must not leak between tests

    def test_search_maps_fields_and_skips_forks_and_archived(self):
        with mock.patch.object(common, "fetch_json", return_value=SEARCH) as fetched:
            items = repos.github_search("agent skills", "agent skills in:name,description stars:>=10", since_date="2026-10-04", now=NOW)
        url = fetched.call_args[0][0]
        self.assertIn("pushed%3A%3E%3D2026-10-04", url)
        self.assertEqual(len(items), 2)  # plain search keeps the off-lane repo; rising does not
        item = items[0]
        self.assertEqual(item["url"], "https://github.com/acme/agent-skills")
        self.assertEqual(item["metrics"]["created"], "2026-10-15")
        self.assertEqual(item["title"], "acme/agent-skills")
        self.assertEqual(item["source"], "github:search:agent skills")
        self.assertEqual(item["metrics"]["stars"], 1200)
        self.assertEqual(item["published_at"], "2026-10-24T10:00:00+00:00")
        self.assertIn("MIT", item["summary"])
        self.assertEqual(set(item), SCHEMA)
        self.assertEqual(item["lane"], "repo")

    def test_watchlist_repo_uses_watchlist_source(self):
        with mock.patch.object(common, "fetch_json", return_value=SEARCH["items"][0]):
            item = repos.github_repo("acme/agent-skills", now=NOW)
        self.assertEqual(item["source"], "github:watchlist")

    def test_gh_token_header_when_present(self):
        with mock.patch.object(common, "fetch_json", return_value=SEARCH) as fetched, mock.patch.dict(os.environ, {"GH_TOKEN": "abc"}):
            repos.github_search("x", "x", since_date="2026-10-04", now=NOW)
        self.assertEqual(fetched.call_args[1]["headers"]["Authorization"], "Bearer abc")

    def test_dead_gh_token_falls_back_to_anonymous(self):
        calls = []

        def fake(url, timeout=25, headers=None):
            calls.append(headers.get("Authorization"))
            if headers.get("Authorization"):
                raise urllib.error.HTTPError(url, 401, "Unauthorized", {}, None)
            return SEARCH

        repos._token_rejected = False
        err = io.StringIO()
        with mock.patch.object(common, "fetch_json", side_effect=fake), mock.patch.dict(os.environ, {"GH_TOKEN": "dead"}), redirect_stderr(err):
            items = repos.github_search("x", "x", since_date="2026-10-04", now=NOW)
            repos.github_search("y", "y", since_date="2026-10-04", now=NOW)
        self.assertEqual(len(items), 2)
        self.assertEqual(calls, ["Bearer dead", None, None])  # retried once, then anonymous for the run
        self.assertIn("GH_TOKEN rejected (401)", err.getvalue())
        repos._token_rejected = False

    def test_rising_query_adds_created_filter_source_and_bonus(self):
        with mock.patch.object(common, "fetch_json", return_value=SEARCH) as fetched, mock.patch.object(
            common, "read_sources", side_effect=lambda s: {"github_queries": [], "github_rising": ["rising agents | ai agent stars:>=100"], "github_watchlist": []}[s]
        ):
            items = repos.collect(now=NOW)
        url = fetched.call_args[0][0]
        self.assertIn("created%3A%3E%3D2026-10-11", url)
        self.assertEqual([i["title"] for i in items], ["acme/agent-skills"])  # genealogy repo dropped: off-lane
        self.assertEqual(items[0]["source"], "github:rising:rising agents")
        self.assertGreaterEqual(items[0]["score"], repos.RISING_BONUS)

    def test_collect_tolerates_failed_source(self):
        seen = []

        def fake(url, timeout=25, headers=None):
            seen.append(url)
            if "search/repositories" in url:
                return SEARCH
            if "/repos/obra/superpowers" in url:
                raise ConnectionError("rate limited")
            if "/repos/" in url:
                return SEARCH["items"][0]
            raise AssertionError(url)

        err = io.StringIO()
        with mock.patch.object(common, "fetch_json", side_effect=fake), mock.patch.object(
            common, "read_sources", side_effect=lambda s: {"github_queries": ["agent skills | agent skills stars:>=10"], "github_rising": [], "github_watchlist": ["acme/agent-skills", "obra/superpowers"]}[s]
        ), redirect_stderr(err):
            items = repos.collect(now=NOW)
        self.assertIn("producer repos: github:watchlist:obra/superpowers failed: ConnectionError", err.getvalue())
        search_urls = [u for u in seen if "search/repositories" in u]
        self.assertTrue(all("created%3A%3E%3D2026-07-27" in u for u in search_urls))  # plain searches: created in the last 90 days
        self.assertEqual(len(items), 2)  # search hit and watchlist hit are the same repo; plus the off-lane one
        self.assertEqual(items[0]["source"], "github:watchlist")


if __name__ == "__main__":
    unittest.main()

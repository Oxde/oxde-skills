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
    def test_search_maps_fields_and_skips_forks_and_archived(self):
        with mock.patch.object(common, "fetch_json", return_value=SEARCH) as fetched:
            items = repos.github_search("agent skills", "agent skills in:name,description stars:>=10", since_date="2026-10-04", now=NOW)
        url = fetched.call_args[0][0]
        self.assertIn("pushed%3A%3E%3D2026-10-04", url)
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["url"], "https://github.com/acme/agent-skills")
        self.assertEqual(item["title"], "acme/agent-skills")
        self.assertEqual(item["source"], "github:search:agent skills")
        self.assertEqual(item["metrics"], {"stars": 1200})
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
        self.assertEqual(len(items), 1)
        self.assertEqual(calls, ["Bearer dead", None, None])  # retried once, then anonymous for the run
        self.assertIn("GH_TOKEN rejected (401)", err.getvalue())
        repos._token_rejected = False

    def test_collect_tolerates_failed_source(self):
        def fake(url, timeout=25, headers=None):
            if "search/repositories" in url:
                return SEARCH
            if "/repos/obra/superpowers" in url:
                raise ConnectionError("rate limited")
            if "/repos/" in url:
                return SEARCH["items"][0]
            raise AssertionError(url)

        err = io.StringIO()
        with mock.patch.object(common, "fetch_json", side_effect=fake), mock.patch.object(
            common, "read_sources", side_effect=lambda s: {"github_queries": ["agent skills | agent skills stars:>=10"], "github_watchlist": ["acme/agent-skills", "obra/superpowers"]}[s]
        ), redirect_stderr(err):
            items = repos.collect(now=NOW)
        self.assertIn("producer repos: github:watchlist:obra/superpowers failed: ConnectionError", err.getvalue())
        self.assertEqual(len(items), 1)  # search hit and watchlist hit are the same repo
        self.assertEqual(items[0]["source"], "github:watchlist")


if __name__ == "__main__":
    unittest.main()

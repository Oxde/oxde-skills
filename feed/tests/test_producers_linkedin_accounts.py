import io
import json
import os
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, linkedin_accounts

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 27, 15, 0, tzinfo=timezone.utc)
POSTS = json.loads((FIX / "apify_linkedin.json").read_text())


class AccountsTest(unittest.TestCase):
    def test_collect_maps_posts_with_watch_source(self):
        for p in POSTS:
            p.pop("query", None)
            p.setdefault("author", {})["universalName"] = "digcreator"
        with mock.patch.object(linkedin_accounts, "fetch_account_posts", return_value=POSTS) as fetched, mock.patch.object(common, "read_sources", return_value=["digcreator", "https://www.linkedin.com/in/stasbel"]):
            items = linkedin_accounts.collect(now=NOW)
        self.assertEqual(fetched.call_args[0][0], ["digcreator", "https://www.linkedin.com/in/stasbel"])
        self.assertEqual(len(items), 2)
        self.assertTrue(all(i["source"] == "linkedin-watch:digcreator" for i in items))
        self.assertTrue(all(i["lane"] == "post" for i in items))

    def test_collect_without_key_reports(self):
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"APIFY_API_KEY": "", "APIFY_TOKEN": ""}), mock.patch.object(common, "read_sources", return_value=["digcreator"]), redirect_stderr(err):
            self.assertEqual(linkedin_accounts.collect(now=NOW), [])
        self.assertIn("producer linkedin_accounts: apify:linkedin-profile-posts failed", err.getvalue())


if __name__ == "__main__":
    unittest.main()

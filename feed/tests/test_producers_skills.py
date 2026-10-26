import io
import json
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, skills

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
CLAWHUB = json.loads((FIX / "clawhub_trending.json").read_text())
SKILLSSH = json.loads((FIX / "skillssh_search.json").read_text())


class ClawhubTest(unittest.TestCase):
    def test_clawhub_maps_fields_and_skips_broken(self):
        with mock.patch.object(common, "fetch_json", return_value=CLAWHUB) as fetched:
            items = skills.clawhub("trending", now=NOW)
        self.assertIn("sort=trending", fetched.call_args[0][0])
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["url"], "https://clawhub.ai/steipete/skills/sonoscli")
        self.assertEqual(first["source"], "clawhub:trending")
        self.assertEqual(first["title"], "Sonoscli")
        self.assertEqual(first["metrics"], {"installs": 2841, "downloads": 90362, "stars": 56})
        self.assertEqual(first["published_at"], "2026-01-04T16:49:41.030000+00:00")
        self.assertEqual(set(first), SCHEMA)
        self.assertTrue(all(i["lane"] == "skill" for i in items))

    def test_score_rewards_niche_terms_and_installs(self):
        with mock.patch.object(common, "fetch_json", return_value=CLAWHUB):
            items = {i["url"].rsplit("/", 1)[-1]: i for i in skills.clawhub("trending", now=NOW)}
        self.assertGreater(items["agent-video-cutter"]["score"], 0)
        self.assertGreater(items["sonoscli"]["score"], 0)
        self.assertTrue(all(0 <= i["score"] <= 100 for i in items.values()))
        self.assertEqual(skills.score("plain words", installs=0, created=None, now=NOW), 0)
        self.assertGreater(skills.score("plain words", installs=10_000, created=None, now=NOW), skills.score("plain words", installs=100, created=None, now=NOW))
        self.assertEqual(skills.score("plain words", installs=4_000_000, created=None, now=NOW), skills.score("plain words", installs=100_000, created=None, now=NOW))  # capped
        self.assertGreater(skills.score("agent skill", installs=100, created=NOW, now=NOW), skills.score("plain words", installs=4_000_000, created=None, now=NOW))
        self.assertGreater(skills.score("x", installs=0, created=NOW, now=NOW), skills.score("x", installs=0, created=None, now=NOW))


class SkillsshTest(unittest.TestCase):
    def test_skillssh_maps_fields(self):
        with mock.patch.object(common, "fetch_json", return_value=SKILLSSH) as fetched:
            items = skills.skillssh("agent skills", now=NOW)
        self.assertIn("q=agent+skills", fetched.call_args[0][0])
        self.assertEqual(items[0]["url"], "https://skills.sh/coreyhaines31/marketingskills/ai-seo")
        self.assertEqual(items[0]["source"], "skillssh:agent skills")
        self.assertEqual(items[0]["title"], "ai-seo (coreyhaines31/marketingskills)")
        self.assertEqual(items[0]["metrics"], {"installs": 150411})
        self.assertEqual(items[0]["score"], skills.score("ai-seo coreyhaines31/marketingskills", installs=150411, created=None, now=NOW))  # query words not scored
        self.assertIsNone(items[0]["published_at"])
        self.assertEqual(set(items[0]), SCHEMA)


class SkillsCollectTest(unittest.TestCase):
    def test_collect_tolerates_failed_source(self):
        def fake(url, timeout=25, headers=None):
            if "clawhub.ai" in url and "createdAt" in url:
                raise ConnectionError("clawhub down")
            if "clawhub.ai" in url:
                return CLAWHUB
            if "skills.sh" in url:
                return SKILLSSH
            raise AssertionError(url)

        err = io.StringIO()
        with mock.patch.object(common, "fetch_json", side_effect=fake), mock.patch.object(
            common, "read_sources", return_value=["agent skills"]
        ), redirect_stderr(err):
            items = skills.collect(now=NOW)
        self.assertIn("producer skills: clawhub:createdAt failed: ConnectionError", err.getvalue())
        self.assertEqual(len(items), 4)
        self.assertTrue(all(set(i) == SCHEMA for i in items))


if __name__ == "__main__":
    unittest.main()

import io
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed.producers import common, news

FIX = Path(__file__).parent / "fixtures"
SCHEMA = {"lane", "source", "title", "url", "summary", "published_at", "score", "metrics"}
NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)


class CommonTest(unittest.TestCase):
    def test_keyword_score_counts_niche_terms(self):
        self.assertGreaterEqual(common.keyword_score("OpenAI ships agent skills"), 4 + 4 + 3)
        self.assertEqual(common.keyword_score("weather tomorrow"), 0)

    def test_recency_score_linear_over_48h(self):
        self.assertEqual(common.recency_score(NOW, NOW), 20)
        self.assertEqual(common.recency_score(NOW.replace(hour=0), NOW), 15)
        self.assertEqual(common.recency_score(None, NOW), 0)
        self.assertEqual(common.recency_score(datetime(2026, 10, 1, tzinfo=timezone.utc), NOW), 0)

    def test_clamp(self):
        self.assertEqual((common.clamp(-5), common.clamp(50), common.clamp(500)), (0, 50, 100))

    def test_resolve_short_link_falls_back_to_input_on_error(self):
        common._resolved.clear()
        with mock.patch.object(common.urllib.request, "urlopen", side_effect=ConnectionError("down")):
            self.assertEqual(common.resolve_short_link("https://lnkd.in/zzz"), "https://lnkd.in/zzz")
        self.assertEqual(common.short_links(["https://lnkd.in/a", "https://github.com/x/y"]), ["https://lnkd.in/a"])

    def test_read_sources_sections(self):
        self.assertEqual(common.read_sources("telegram")[0], "data_secrets")
        self.assertEqual(len(common.read_sources("rss")), 4)
        self.assertEqual(common.read_sources("github_queries")[0], "agent skills | agent skills in:name,description stars:>=10")
        self.assertEqual(common.read_sources("nope"), [])


class NewsParseTest(unittest.TestCase):
    def test_parse_telegram_fixture_yields_items_with_tg_source(self):
        items = news.parse_telegram((FIX / "telegram_channel.html").read_text(), "data_secrets")
        self.assertEqual(len(items), 2)  # the 'short' service post is skipped
        first = items[0]
        self.assertEqual(first["source"], "tg:data_secrets")
        self.assertEqual(first["url"], "https://t.me/data_secrets/100")
        self.assertEqual(first["published_at"], "2026-10-25T08:30:00+00:00")
        self.assertTrue(first["title"].startswith("OpenAI released a new agent SDK"))
        self.assertIn("один главный агент", items[1]["summary"])
        self.assertEqual(set(first), SCHEMA)

    def test_parse_rss_and_atom_fixtures(self):
        rss = news.parse_rss((FIX / "rss.xml").read_text(), "https://techcrunch.com/feed")
        self.assertEqual(len(rss), 2)  # empty-title entry dropped
        self.assertEqual(rss[0]["source"], "rss:techcrunch.com")
        self.assertEqual(rss[0]["published_at"], "2026-10-25T09:00:00+00:00")
        self.assertEqual(rss[0]["summary"], "Anthropic announced a runtime that lets agents run for hours.")
        atom = news.parse_rss((FIX / "atom.xml").read_text(), "https://www.theverge.com/rss")
        self.assertEqual(atom[0]["url"], "https://www.theverge.com/2026/10/25/google-agent-chats")
        self.assertEqual(atom[0]["source"], "rss:theverge.com")
        self.assertEqual(atom[0]["published_at"], "2026-10-25T07:00:00+00:00")


class NewsCollectTest(unittest.TestCase):
    def _fake_fetch(self, url, timeout=25):
        if "t.me/s/data_secrets" in url:
            return (FIX / "telegram_channel.html").read_text()
        if "techcrunch" in url:
            return (FIX / "rss.xml").read_text()
        raise ConnectionError(f"boom {url}")

    def test_collect_skips_failed_source_and_reports_to_stderr(self):
        err = io.StringIO()
        with mock.patch.object(common, "fetch", side_effect=self._fake_fetch), mock.patch.object(
            common, "read_sources", side_effect=lambda s: {"telegram": ["data_secrets", "broken"], "rss": ["https://techcrunch.com/feed", "https://down.example/rss"]}[s]
        ), redirect_stderr(err):
            items = news.collect(now=NOW)
        urls = {i["url"] for i in items}
        self.assertIn("https://t.me/data_secrets/100", urls)
        self.assertIn("https://techcrunch.com/2026/10/25/anthropic-agent-runtime/?utm_source=rss", urls)
        self.assertNotIn("https://techcrunch.com/2026/10/20/ai-security-raise/", urls)  # older than 30h
        self.assertIn("producer news: tg:broken failed: ConnectionError", err.getvalue())
        self.assertIn("producer news: rss:down.example failed: ConnectionError", err.getvalue())
        self.assertTrue(all(set(i) == SCHEMA for i in items))
        self.assertTrue(all(i["lane"] == "news" for i in items))
        self.assertTrue(all(0 <= i["score"] <= 100 for i in items))
        top = max(items, key=lambda i: i["score"])
        self.assertIn("agent", (top["title"] + top["summary"]).lower())


if __name__ == "__main__":
    unittest.main()

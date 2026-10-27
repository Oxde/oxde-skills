import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from feed.store import PROVEN_BONUS, Store, canonical_url, extract_links, item_id, similar, title_key, velocity, velocity_bonus

NOW = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
TOMORROW = NOW + timedelta(days=1)

NEWS_ITEM = {
    "lane": "news",
    "source": "rss:techcrunch",
    "title": "Anthropic ships a new agent runtime for Claude",
    "url": "https://techcrunch.com/2026/10/25/anthropic-agent-runtime/",
    "summary": "Anthropic announced a runtime.",
    "published_at": "2026-10-25T09:00:00+00:00",
    "score": 40,
    "metrics": {},
}
NEWS_ID = item_id(NEWS_ITEM["url"])

SKILL_ITEM = {
    "lane": "skill",
    "source": "clawhub:trending",
    "title": "video-cutter",
    "url": "https://clawhub.ai/someone/skills/video-cutter",
    "summary": "Cuts video.",
    "published_at": None,
    "score": 55,
    "metrics": {"installs": 120},
}
SKILL_ID = item_id(SKILL_ITEM["url"])


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.tmp.name) / "feed.db"))

    def tearDown(self):
        self.tmp.cleanup()


class CanonicalTest(unittest.TestCase):
    def test_canonical_url_strips_tracking_and_normalizes(self):
        self.assertEqual(
            canonical_url("HTTP://TechCrunch.com/a/?utm_source=x&id=2#top"),
            "https://techcrunch.com/a?id=2",
        )
        self.assertEqual(item_id("https://techcrunch.com/a/"), item_id("http://techcrunch.com/a"))
        self.assertEqual(len(item_id("https://x.y/z")), 16)

    def test_title_similarity(self):
        a = title_key("Anthropic ships a new agent runtime for Claude")
        b = title_key("Anthropic ships a new agent runtime for Claude!")
        c = title_key("OpenAI raises prices for enterprise customers")
        self.assertTrue(similar(a, b))
        self.assertFalse(similar(a, c))
        self.assertFalse(similar(title_key("GPT-5 is out"), title_key("GPT-6 is out")))


class IngestTest(StoreTestCase):
    def test_ingest_inserts_once_and_counts_duplicates(self):
        r1 = self.store.ingest([NEWS_ITEM], now=NOW)
        r2 = self.store.ingest([NEWS_ITEM], now=NOW)
        self.assertEqual((r1["inserted"], r2["inserted"], r2["duplicates"]), (1, 0, 1))
        item = self.store.get(NEWS_ID)
        self.assertEqual(item["status"], "new")
        self.assertEqual(item["owner"], "oxde")
        self.assertEqual(item["collected_at"], NOW.isoformat())

    def test_ingest_rejects_missing_url_or_title(self):
        r = self.store.ingest([{"lane": "news", "title": "x"}, {"lane": "news", "url": "https://a.b/c"}], now=NOW)
        self.assertEqual(r["rejected"], 2)
        self.assertEqual(r["inserted"], 0)

    def test_ingest_rejects_non_http_schemes(self):
        r = self.store.ingest([{**NEWS_ITEM, "url": "javascript:alert(1)"}, {**NEWS_ITEM, "url": "ftp://x.y/z"}], now=NOW)
        self.assertEqual((r["rejected"], r["inserted"]), (2, 0))

    def test_similar_title_same_lane_within_7_days_is_duplicate(self):
        self.store.ingest([NEWS_ITEM], now=NOW)
        r = self.store.ingest(
            [{**NEWS_ITEM, "url": "https://t.me/data_secrets/123", "title": NEWS_ITEM["title"] + "!"}],
            now=NOW + timedelta(days=2),
        )
        self.assertEqual(r["duplicates"], 1)
        self.assertEqual(r["inserted"], 0)

    def test_similar_title_in_other_lane_is_not_duplicate(self):
        self.store.ingest([NEWS_ITEM], now=NOW)
        r = self.store.ingest([{**NEWS_ITEM, "lane": "repo", "url": "https://github.com/x/y"}], now=NOW)
        self.assertEqual(r["inserted"], 1)

    def test_similar_title_older_than_7_days_is_not_duplicate(self):
        self.store.ingest([NEWS_ITEM], now=NOW - timedelta(days=8))
        r = self.store.ingest([{**NEWS_ITEM, "url": "https://other.site/post"}], now=NOW)
        self.assertEqual(r["inserted"], 1)

    def test_reingest_merges_metrics_keeps_status(self):
        self.store.ingest([SKILL_ITEM], now=NOW)
        self.store.update(SKILL_ID, status="shown")
        self.store.ingest([{**SKILL_ITEM, "metrics": {"installs": 200}, "score": 60}], now=TOMORROW)
        item = self.store.get(SKILL_ID)
        self.assertEqual(item["status"], "shown")
        self.assertEqual(item["score"], 60 + velocity_bonus({"a": {"installs": 120}, "b": {"installs": 200}}))  # grew, so it earns a bonus
        metrics = json.loads(item["metrics"])
        self.assertEqual(set(metrics), {"2026-10-25", "2026-10-26"})
        self.assertEqual(metrics["2026-10-26"]["installs"], 200)
        self.assertEqual(item["collected_at"], NOW.isoformat())

    def test_get_unknown_returns_none(self):
        self.assertIsNone(self.store.get("nope"))


class MigrationTest(unittest.TestCase):
    def test_old_database_without_kind_column_is_migrated(self):
        import sqlite3

        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / "old.db")
            conn = sqlite3.connect(path)
            conn.executescript(Store.__init__.__globals__["SCHEMA"].replace(",\n    kind TEXT NOT NULL DEFAULT ''", ""))
            conn.close()
            store = Store(path)
            store.ingest([NEWS_ITEM], now=NOW)
            self.assertEqual(store.get(NEWS_ID)["kind"], "")


class VelocityTest(StoreTestCase):
    def test_velocity_and_bonus(self):
        hist = {"2026-10-25": {"stars": 100}, "2026-10-27": {"stars": 350, "installs": 5}, "2026-10-26": {"stars": 200}}
        self.assertEqual(velocity(hist), {"stars": 250})
        self.assertEqual(velocity({"2026-10-25": {"stars": 100}}), {})
        self.assertEqual(velocity_bonus({}), 0)
        self.assertEqual(velocity_bonus(hist), 30)  # 100 -> 350 stars is 250%
        self.assertEqual(velocity_bonus({"a": {"installs": 839_034}, "b": {"installs": 840_194}}), 0)  # +1160 on 839k is noise
        self.assertEqual(velocity_bonus({"a": {"installs": 1000}, "b": {"installs": 1050}}), 10)  # 5%
        self.assertLessEqual(velocity_bonus({"a": {"stars": 0}, "b": {"stars": 10**6}}), 30)

    def test_reingest_adds_velocity_bonus_to_score(self):
        self.store.ingest([{**SKILL_ITEM, "metrics": {"stars": 100}, "score": 40}], now=NOW)
        self.store.ingest([{**SKILL_ITEM, "metrics": {"stars": 400}, "score": 40}], now=TOMORROW)
        self.assertEqual(self.store.get(SKILL_ID)["score"], 40 + velocity_bonus({"a": {"stars": 100}, "b": {"stars": 400}}))


class PerformerTest(StoreTestCase):
    POST = {"lane": "post", "source": "linkedin:agent skills", "title": "Sandhya: Claude Code can now make a knowledge graph prove its answers.",
            "url": "https://www.linkedin.com/posts/digcreator_x-activity-1", "summary": "Claude Code can now make a knowledge graph prove its answers. Fabio open-sourced it: https://github.com/fabio/open-ontologies/tree/main works today.",
            "published_at": "2026-10-23T10:00:00+00:00", "score": 60, "metrics": {"likes": 794, "comments": 16, "shares": 82, "author": "Sandhya Ahuja"}}
    REPO = {"lane": "repo", "source": "github:search:agent skills", "title": "fabio/open-ontologies", "url": "https://github.com/fabio/open-ontologies",
            "summary": "knowledge graphs with proofs", "published_at": "2026-10-22T10:00:00+00:00", "score": 50, "metrics": {"stars": 900}}

    def test_extract_links_normalizes_repo_urls(self):
        self.assertEqual(extract_links("see https://github.com/fabio/open-ontologies/tree/main and https://skills.sh/a/b/c."), ["https://github.com/fabio/open-ontologies", "https://skills.sh/a/b/c"])

    def test_linkedin_post_with_engagement_becomes_performer(self):
        self.store.ingest([self.POST], now=NOW)
        item = self.store.get(item_id(self.POST["url"]))
        self.assertEqual(item["kind"], "performer")
        self.assertEqual(json.loads(item["metrics"])[NOW.date().isoformat()]["links"], ["https://github.com/fabio/open-ontologies"])
        low = {**self.POST, "url": "https://www.linkedin.com/posts/x-activity-2", "title": "someone: a quiet post about agents", "metrics": {"likes": 12}}
        self.store.ingest([low], now=NOW)
        self.assertEqual(self.store.get(item_id(low["url"]))["kind"], "")

    def test_repo_linked_by_performer_is_boosted_whichever_arrives_first(self):
        self.store.ingest([self.POST], now=NOW)
        self.store.ingest([self.REPO], now=NOW)
        repo = self.store.get(item_id(self.REPO["url"]))
        self.assertEqual(repo["score"], 50 + PROVEN_BONUS)
        self.assertIn("proven: posted on LinkedIn by Sandhya Ahuja with 794 likes", repo["why"])
        other = Store(str(Path(self.tmp.name) / "other.db"))
        other.ingest([self.REPO], now=NOW)
        other.ingest([self.POST], now=NOW)
        repo2 = other.get(item_id(self.REPO["url"]))
        self.assertEqual(repo2["score"], 50 + PROVEN_BONUS)
        self.assertIn("proven:", repo2["why"])

    def test_performers_query_orders_by_likes(self):
        self.store.ingest([self.POST, {**self.POST, "url": "https://www.linkedin.com/posts/y-activity-3", "title": "other: Someone built Git for AI agent memory", "summary": "Someone built Git for AI agent memory.", "metrics": {"likes": 1071, "author": "S"}}], now=NOW)
        perf = self.store.performers(days=30)
        self.assertEqual([json.loads(i["metrics"])[NOW.date().isoformat()]["likes"] for i in perf], [1071, 794])
        self.assertEqual(self.store.performers(days=30, min_likes=1000)[0]["title"], "other: Someone built Git for AI agent memory")


class ExpireTest(StoreTestCase):
    def test_expire_marks_old_new_offered_shown(self):
        self.store.ingest([NEWS_ITEM], now=NOW - timedelta(days=15))
        self.store.ingest([SKILL_ITEM], now=NOW - timedelta(days=15))
        self.store.update(SKILL_ID, status="picked")
        self.assertEqual(self.store.expire(now=NOW), 1)
        self.assertEqual(self.store.get(NEWS_ID)["status"], "expired")
        self.assertEqual(self.store.get(SKILL_ID)["status"], "picked")

    def test_expire_leaves_fresh_items(self):
        self.store.ingest([NEWS_ITEM], now=NOW - timedelta(days=13))
        self.assertEqual(self.store.expire(now=NOW), 0)


if __name__ == "__main__":
    unittest.main()


WORDS = ("anthropic", "openai", "mistral", "google", "meta", "hermes", "codex", "claude")


def _mk(lane, n, score=10, source=None, published=None):
    return {
        "lane": lane,
        "source": source or f"src:{lane}",
        "title": f"{lane} {WORDS[n % len(WORDS)]} story {n} about {WORDS[(n * 3) % len(WORDS)]} agents",
        "url": f"https://example.com/{lane}/{n}",
        "summary": "",
        "published_at": published,
        "score": score,
        "metrics": {},
    }


class MenuTest(StoreTestCase):
    def test_menu_respects_quota_and_marks_offered(self):
        items = [_mk("news", i) for i in range(6)] + [_mk("skill", i) for i in range(3)] + [_mk("repo", 0)]
        self.store.ingest(items, now=NOW)
        menu = self.store.menu({"news": 4, "skill": 2, "repo": 2}, now=NOW)
        from collections import Counter

        self.assertEqual(Counter(i["lane"] for i in menu), {"news": 5, "skill": 2, "repo": 1})
        self.assertTrue(all(i["status"] == "offered" for i in menu))
        self.assertTrue(all(i["offer_count"] == 1 for i in menu))
        self.assertTrue(all(i["offered_at"] == NOW.isoformat() for i in menu))

    def test_menu_orders_by_score_then_recency(self):
        self.store.ingest(
            [
                _mk("news", 1, score=10, published="2026-10-25T08:00:00+00:00"),
                _mk("news", 2, score=50, published="2026-10-24T08:00:00+00:00"),
                _mk("news", 3, score=10, published="2026-10-25T11:00:00+00:00"),
            ],
            now=NOW,
        )
        menu = self.store.menu({"news": 3}, now=NOW)
        self.assertEqual([i["url"][-1] for i in menu], ["2", "3", "1"])

    def test_offered_item_returns_at_most_twice(self):
        self.store.ingest([_mk("news", 1)], now=NOW)
        for _ in range(2):
            self.assertEqual(len(self.store.menu({"news": 1}, now=NOW)), 1)
        self.assertEqual(self.store.menu({"news": 1}, now=NOW), [])

    def test_shown_item_never_returns(self):
        self.store.ingest([_mk("news", 1)], now=NOW)
        iid = item_id("https://example.com/news/1")
        self.store.update(iid, status="shown")
        self.assertEqual(self.store.menu({"news": 1}, now=NOW), [])

    def test_menu_on_empty_store_is_empty_list(self):
        self.assertEqual(self.store.menu({"news": 4, "skill": 2, "repo": 2}, now=NOW), [])

    def test_menu_excludes_frameworks_by_default(self):
        self.store.ingest([_mk("repo", 1, score=90), _mk("repo", 2, score=10)], now=NOW)
        self.store.update(item_id("https://example.com/repo/1"), kind="framework")
        menu = self.store.menu({"repo": 2}, now=NOW)
        self.assertEqual([i["url"][-1] for i in menu], ["2"])
        self.assertEqual(len(self.store.menu({"repo": 2}, now=NOW, exclude_kinds="")), 2)

    def test_menu_rejects_unknown_lane(self):
        with self.assertRaises(ValueError):
            self.store.menu({"bogus": 1}, now=NOW)


class UpdateListTest(StoreTestCase):
    def test_update_status_sets_timestamps_and_rejects_unknown(self):
        self.store.ingest([NEWS_ITEM], now=NOW)
        item = self.store.update(NEWS_ID, status="shown", insight="one line", why="because", now=NOW)
        self.assertEqual((item["status"], item["insight"], item["why"], item["shown_at"]), ("shown", "one line", "because", NOW.isoformat()))
        item = self.store.update(NEWS_ID, status="picked", pick_note="news post about 2", now=TOMORROW)
        self.assertEqual((item["picked_at"], item["pick_note"]), (TOMORROW.isoformat(), "news post about 2"))
        with self.assertRaises(ValueError):
            self.store.update(NEWS_ID, status="bogus")
        with self.assertRaises(ValueError):
            self.store.update(NEWS_ID, title="nope")
        with self.assertRaises(ValueError):
            self.store.update(NEWS_ID, kind="gadget")
        self.assertEqual(self.store.update(NEWS_ID, kind="framework")["kind"], "framework")
        self.assertEqual(len(self.store.list(exclude_kinds="framework")), 0)
        self.assertEqual(len(self.store.list(exclude_kinds="pack")), 1)
        with self.assertRaises(KeyError):
            self.store.update("nope", status="shown")

    def test_list_filters_by_status_lane_since(self):
        self.store.ingest([_mk("news", 1), _mk("skill", 1)], now=NOW - timedelta(days=2))
        self.store.ingest([_mk("news", 2)], now=NOW)
        self.store.update(item_id("https://example.com/news/2"), status="shown")
        self.assertEqual(len(self.store.list()), 3)
        self.assertEqual(len(self.store.list(lane="news")), 2)
        self.assertEqual(len(self.store.list(status="shown")), 1)
        self.assertEqual(len(self.store.list(status="new,shown")), 3)
        self.assertEqual(len(self.store.list(since=NOW - timedelta(days=1))), 1)
        self.assertEqual(len(self.store.list(limit=2)), 2)
        self.assertEqual(len(self.store.list(lane="news,skill")), 3)
        by_score = self.store.list(order="score")
        self.assertEqual([i["score"] for i in by_score], sorted((i["score"] for i in by_score), reverse=True))
        with self.assertRaises(ValueError):
            self.store.list(order="bogus")


class StatsTest(StoreTestCase):
    def test_stats_counts_per_lane_and_source_pick_rate(self):
        self.store.ingest(
            [
                _mk("news", 1, source="rss:techcrunch"),
                _mk("news", 2, source="rss:techcrunch"),
                _mk("skill", 1, source="clawhub:trending"),
            ],
            now=NOW - timedelta(hours=1),
        )
        self.store.menu({"news": 2, "skill": 1}, now=NOW)
        self.store.update(item_id("https://example.com/news/1"), status="shown", now=NOW)
        self.store.update(item_id("https://example.com/news/1"), status="picked", now=NOW)
        self.store.update(item_id("https://example.com/news/2"), status="shown", now=NOW)
        stats = self.store.stats(days=7, now=NOW)
        self.assertEqual(stats["days"], 7)
        self.assertEqual(stats["lanes"]["news"], {"collected": 2, "offered": 2, "shown": 2, "picked": 1, "posted": 0})
        self.assertEqual(stats["lanes"]["skill"]["collected"], 1)
        self.assertEqual(stats["sources"][0], {"source": "rss:techcrunch", "collected": 2, "picked": 1, "pick_rate": 0.5})
        self.assertEqual(stats["last_collected"]["rss"], (NOW - timedelta(hours=1)).isoformat())
        self.assertIn("clawhub", stats["last_collected"])

    def test_stats_ignores_items_older_than_window(self):
        self.store.ingest([_mk("news", 1)], now=NOW - timedelta(days=10))
        stats = self.store.stats(days=7, now=NOW)
        self.assertEqual(stats["lanes"]["news"]["collected"], 0)

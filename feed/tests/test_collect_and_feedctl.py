import io
import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from feed import collect, feedctl
from feed.service import make_server
from feed.store import Store

TOKEN = "tok"
NOW = datetime(2026, 10, 25, 9, 40, tzinfo=timezone.utc)


def _item(lane, n, score=10):
    return {
        "lane": lane,
        "source": f"src:{lane}",
        "title": f"{lane} story {n} about {('alpha', 'beta', 'gamma', 'delta')[n % 4]} agents",
        "url": f"https://example.com/{lane}/{n}",
        "summary": "",
        "published_at": None,
        "score": score,
        "metrics": {"installs": 100 * n} if lane != "news" else {},
    }


class RunTest(unittest.TestCase):
    def test_run_continues_after_one_producer_fails_and_exits_0(self):
        posted = []
        producers = {"news": lambda: [_item("news", 1)], "skills": mock.Mock(side_effect=RuntimeError("boom")), "repos": lambda: [_item("repo", 1), _item("repo", 2)]}
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = collect.run(producers, post=lambda items: posted.append(items) or {"inserted": 3, "duplicates": 0, "rejected": 0, "expired": 0})
        self.assertEqual(code, 0)
        self.assertEqual(len(posted[0]), 3)
        self.assertEqual(out.getvalue().strip(), "collect: news=1 skills=0 repos=2 inserted=3 duplicates=0 rejected=0 expired=0 failed=[skills]")
        self.assertIn("producer skills failed: RuntimeError: boom", err.getvalue())

    def test_run_exits_1_when_all_fail(self):
        producers = {"news": mock.Mock(side_effect=RuntimeError("a")), "skills": mock.Mock(side_effect=RuntimeError("b"))}
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = collect.run(producers, post=lambda items: self.fail("must not post"))
        self.assertEqual(code, 1)

    def test_run_exits_1_when_post_fails(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = collect.run({"news": lambda: [_item("news", 1)]}, post=mock.Mock(side_effect=ConnectionError("down")))
        self.assertEqual(code, 1)


class RenderTest(unittest.TestCase):
    def test_render_menu_matches_golden(self):
        items = [
            {**_item("news", 1, 80), "id": "aaaa000000000001", "source": "rss:techcrunch.com"},
            {**_item("news", 2, 70), "id": "aaaa000000000002", "source": "tg:data_secrets"},
            {**_item("skill", 1, 60), "id": "bbbb000000000001", "source": "clawhub:trending", "metrics": json.dumps({"2026-10-25": {"installs": 100, "stars": 3}})},
            {**_item("repo", 1, 50), "id": "cccc000000000001", "source": "github:watchlist", "metrics": json.dumps({"2026-10-25": {"stars": 1200}})},
        ]
        golden = "\n".join([
            "Research menu · Sun 25 Oct, morning",
            "",
            "NEWS",
            "1. news story 1 about beta agents — https://example.com/news/1",
            "   id: aaaa000000000001 · score 80 · rss:techcrunch.com",
            "2. news story 2 about gamma agents — https://example.com/news/2",
            "   id: aaaa000000000002 · score 70 · tg:data_secrets",
            "",
            "SKILLS",
            "3. skill story 1 about beta agents — https://example.com/skill/1",
            "   id: bbbb000000000001 · score 60 · clawhub:trending · installs 100 · stars 3",
            "",
            "REPOS",
            "4. repo story 1 about beta agents — https://example.com/repo/1",
            "   id: cccc000000000001 · score 50 · github:watchlist · stars 1200",
            "",
            'Reply with a number and what you want: "news post about 2", "video 3", "skip all".',
        ])
        self.assertEqual(feedctl.render_menu(items, now=NOW), golden)
        self.assertIn(", afternoon", feedctl.render_menu(items, now=NOW.replace(hour=15)))

    def test_render_menu_adds_summary_line_when_present(self):
        item = {**_item("news", 1, 80), "id": "aaaa000000000001", "source": "tg:data_secrets", "summary": "OpenAI открыла Decisions API.\nВторая строка " + "x" * 300}
        text = feedctl.render_menu([item], now=NOW)
        line = [l for l in text.splitlines() if l.startswith("   summary:")][0]
        self.assertTrue(line.startswith("   summary: OpenAI открыла Decisions API. Вторая строка"))
        self.assertLessEqual(len(line), 3 + len("summary: ") + 220 + 1)

    def test_render_menu_shows_growth_since_first_seen(self):
        item = {**_item("repo", 1, 80), "id": "cccc000000000002", "source": "github:rising:x", "metrics": json.dumps({"2026-10-23": {"stars": 100, "created": "2026-10-20"}, "2026-10-25": {"stars": 340, "created": "2026-10-20"}})}
        text = feedctl.render_menu([item], now=NOW)
        self.assertIn("stars 340 · created 2026-10-20 · +240 stars since 2026-10-23", text)

    def test_render_videos_groups_by_creator_outlier_first(self):
        items = [
            {**_item("video", 1, 70), "id": "v1", "source": "instagram:nick", "summary": "Comment CLONE", "published_at": "2026-10-25T10:00:00+00:00", "metrics": json.dumps({"2026-10-26": {"plays": 66056, "likes": 1207, "comments": 1362, "duration": 38.4, "outlier": 0.87, "creator": "nick"}})},
            {**_item("video", 2, 80), "id": "v2", "source": "instagram:chase", "summary": "Comment agent", "published_at": "2026-10-24T10:00:00+00:00", "metrics": json.dumps({"2026-10-26": {"plays": 61074, "likes": 1500, "comments": 300, "duration": 30.0, "outlier": 3.82, "creator": "chase"}})},
        ]
        text = feedctl.render_videos(items, 7, now=NOW)
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("Competitor reels · last 7 days"))
        self.assertLess(lines.index("@chase"), lines.index("@nick"))  # higher outlier first
        self.assertIn("1. 3.82x · 61074 plays · 1500 likes · 300 comments · 30.0s · 2026-10-24", text)
        self.assertIn("   id: v2 · https://example.com/video/2", text)
        self.assertIn("   caption: Comment agent", text)
        self.assertEqual(feedctl.render_videos([], 7, now=NOW), "Video desk: no reels.")

    def test_render_menu_empty(self):
        self.assertEqual(feedctl.render_menu([], now=NOW), "Research menu: nothing new.")

    def test_render_stats(self):
        stats = {"days": 7, "lanes": {"news": {"collected": 10, "offered": 6, "shown": 4, "picked": 1, "posted": 1}, "skill": {"collected": 0, "offered": 0, "shown": 0, "picked": 0, "posted": 0}},
                 "sources": [{"source": "rss:techcrunch.com", "collected": 10, "picked": 1, "pick_rate": 0.1}], "last_collected": {"rss": "2026-10-25T07:00:00+00:00"}}
        text = feedctl.render_stats(stats)
        self.assertIn("Feed stats · last 7 days", text)
        self.assertIn("news: collected 10 · offered 6 · shown 4 · picked 1 · posted 1", text)
        self.assertIn("rss:techcrunch.com 1/10 (10%)", text)
        self.assertIn("rss 2026-10-25T07:00", text)


class LiveClientTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "public").mkdir()
        self.store = Store(str(root / "feed.db"))
        self.server = make_server(self.store, str(root / "public"), TOKEN, host="127.0.0.1", port=0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = mock.patch.dict(os.environ, {"FEED_URL": f"http://127.0.0.1:{self.server.server_address[1]}", "FEED_TOKEN": TOKEN})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def _cli(self, argv, stdin=""):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err), mock.patch("sys.stdin", io.StringIO(stdin)):
            code = feedctl.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_feedctl_roundtrip_against_live_service(self):
        lines = "\n".join(json.dumps(_item("news", i, 50 + i)) for i in range(3)) + "\n" + json.dumps(_item("skill", 1, 40))
        code, out, _ = self._cli(["ingest"], stdin=lines)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["inserted"], 4)
        code, out, _ = self._cli(["menu", "--quota", "news=2,skill=2"])  # explicit quota; default now includes post
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Research menu ·"))
        self.assertIn("SKILLS", out)
        ids = [line.split()[1] for line in out.splitlines() if line.strip().startswith("id:")]
        self.assertEqual(len(ids), 4)  # skill lane is short by one, news backfills the slot
        code, out, _ = self._cli(["set-status", ids[0], "shown", "--insight", "the limit moved", "--why", "you hit it last week"])
        self.assertEqual(code, 0)
        code, out, _ = self._cli(["pick", ids[0], "--note", "news post about 1"])
        self.assertEqual(code, 0)
        item = self.store.get(ids[0])
        self.assertEqual((item["status"], item["insight"], item["why"], item["pick_note"]), ("picked", "the limit moved", "you hit it last week", "news post about 1"))
        code, out, _ = self._cli(["list"])
        self.assertEqual(code, 0)
        self.assertIn(f"{ids[0]} · picked · news ·", out)
        self.assertEqual(sum(1 for l in out.splitlines() if " · " in l and not l.startswith(" ")), 4)  # one row per item, reason lines indented
        code, out, _ = self._cli(["list", "--status", "new"])
        self.assertEqual(out.strip(), "No items.")
        code, out, _ = self._cli(["top", "--lanes", "news,skill", "--n", "2"])
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("Skill desk candidates ·"))
        self.assertEqual(out.count("\n   id: "), 2)
        self.assertIn("· status offered · score 51 ·", out.splitlines()[2])  # highest eligible first; picked (52) excluded by default
        self.assertNotIn("picked", out)
        code, out, _ = self._cli(["top", "--lanes", "repo"])
        self.assertEqual(out.strip(), "Skill desk: no candidates.")
        code, out, _ = self._cli(["top", "--lanes", "news,skill", "--n", "4"])
        self.assertIn("[skill]", out)  # the lower-scored lane still gets its share
        self.assertEqual(out.count("\n   id: "), 3)  # 2 news + 1 skill available
        self._cli(["set-status", ids[1], "skipped", "--why", "generic: another x", "--kind", "framework"])
        code, out, _ = self._cli(["top", "--lanes", "news,skill", "--n", "4"])
        self.assertEqual(out.count("\n   id: "), 2)
        self.assertIn("Recently skipped (Mark's bar; do not resurface these):", out)
        self.assertIn("— generic: another x", out)
        code, out, _ = self._cli(["list", "--status", "skipped"])
        self.assertIn("· skipped · news · framework ·", out)
        self.assertIn("   why: generic: another x", out)
        self._cli(["set-status", ids[2], "shown", "--kind", "framework"])
        code, out, _ = self._cli(["top", "--lanes", "news,skill", "--n", "4"])
        self.assertEqual(out.count("\n   id: "), 1)  # frameworks are excluded from the desk by default
        code, out, _ = self._cli(["stats", "--days", "7"])
        self.assertEqual(code, 0)
        self.assertIn("news: collected 3", out)
        code, out, _ = self._cli(["menu"])
        self.assertIn("skill story", out)  # the only item still eligible: offered once, not shown, not skipped
        self.assertNotIn("news story", out)
        code, out, _ = self._cli(["menu"])
        self.assertEqual(out.strip(), "Research menu: nothing new.")  # two offers each, never shown

    def test_feedctl_reports_http_error_with_body(self):
        code, out, err = self._cli(["set-status", "nope", "shown"])
        self.assertEqual(code, 1)
        self.assertIn("404", err)
        self.assertIn("unknown item nope", err)
        with mock.patch.dict(os.environ, {"FEED_TOKEN": "wrong"}):
            code, out, err = self._cli(["stats"])
        self.assertEqual(code, 1)
        self.assertIn("401", err)

    def test_collect_main_posts_through_feedctl(self):
        with mock.patch.object(collect, "PRODUCERS", {"news": lambda: [_item("news", 9)]}), redirect_stdout(io.StringIO()):
            code = collect.main()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.store.list()), 1)


if __name__ == "__main__":
    unittest.main()

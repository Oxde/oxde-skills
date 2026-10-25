import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from feed.service import make_server
from feed.store import Store

ROOT = Path(__file__).resolve().parents[2]
FEED = ROOT / "feed"


class RunMenuScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "public").mkdir()
        self.store = Store(str(root / "feed.db"))
        self.server = make_server(self.store, str(root / "public"), "tok", host="127.0.0.1", port=0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = {**os.environ, "FEED_URL": f"http://127.0.0.1:{self.server.server_address[1]}", "FEED_TOKEN": "tok", "PYTHON": sys.executable}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def test_run_menu_prints_nothing_new_on_empty_service(self):
        result = subprocess.run(["bash", str(FEED / "run_menu.sh")], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Research menu: nothing new.\n")

    def test_run_stats_prints_header(self):
        result = subprocess.run(["bash", str(FEED / "run_stats.sh")], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("Feed stats · last 7 days"))

    def test_ctl_wrapper_runs_feedctl_from_anywhere(self):
        env = {**self.env, "HOME": self.tmp.name}
        result = subprocess.run(["bash", str(FEED / "ctl.sh"), "stats"], env=env, cwd=self.tmp.name, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("Feed stats"))

    def test_run_skill_desk_prints_no_candidates_on_empty_service(self):
        result = subprocess.run(["bash", str(FEED / "run_skill_desk.sh")], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "Skill desk: no candidates.\n")

    def test_skill_desk_prompt_contains_contract(self):
        text = (FEED / "prompts" / "skill_desk.md").read_text()
        for needle in ("Skill desk: no candidates.", "reply exactly `[SILENT]`", "set-status <id> skipped --kind", "Vs <known option>", "Verdict: <strong | watch>", "Angle:", "Kind: <skill | tool | pack>", "Post: \"<first line>\"", "--kind framework", "read Mark's bar", "Useful beats\nnew", "Domain roundup", '"draft 1"', "never publish, install, execute"):
            self.assertIn(needle, text, needle)

    def test_run_collect_script_is_executable_and_points_at_collect(self):
        text = (FEED / "run_collect.sh").read_text()
        self.assertIn("feed.collect", text)
        self.assertTrue(os.access(FEED / "run_collect.sh", os.X_OK))
        self.assertTrue(os.access(FEED / "run_menu.sh", os.X_OK))


class HermesFilesTest(unittest.TestCase):
    def test_prompt_contains_gate_and_silent_rule(self):
        text = (FEED / "prompts" / "menu.md").read_text()
        for needle in (
            "Why would Mark's audience care?",
            "Audience: <why the audience cares>",
            "Why now?",
            "What could a generic AI creator not honestly write here?",
            "at most one verification fetch per item",
            "feed-ctl.sh set-status",
            "set-status <id> skipped",
            "Never invent a number",
            "POSTS",
            "never a fact source on its own",
            "--insight",
            "reply exactly `[SILENT]`",
            "Research menu: nothing new",
        ):
            self.assertIn(needle, text, needle)

    def test_skill_frontmatter_valid(self):
        lines = (FEED / "SKILL.md").read_text().splitlines()
        self.assertEqual(lines[0], "---")
        self.assertIn("name: feed", lines[1:6])
        self.assertTrue(any(l.startswith("description:") for l in lines[1:6]))
        self.assertIn("---", lines[2:8])
        text = "\n".join(lines)
        self.assertIn("feed-ctl.sh pick", text)
        self.assertIn("linkedin-writer", text)
        self.assertIn("set-status", text)

    def test_cron_doc_has_no_job_ids_and_names_three_jobs(self):
        text = (FEED / "CRON.md").read_text()
        for name in ("feed-menu", "feed-collect", "feed-stats", "skill-desk"):
            self.assertIn(name, text)
        self.assertIn("30 9,16 * * *", text)
        self.assertIn("--monitor-script", text)  # the doc explains why it is not used
        self.assertNotIn("1f990ab4df95", text)
        self.assertNotIn("dfbc156f55c1", text)

    def test_old_cron_docs_point_to_feed(self):
        for old in (ROOT / "linkedin" / "overlays" / "oxde" / "cron" / "editorial-radar.md", ROOT / "radar" / "CRON.md"):
            self.assertIn("feed/CRON.md", old.read_text()[:600], old)


if __name__ == "__main__":
    unittest.main()

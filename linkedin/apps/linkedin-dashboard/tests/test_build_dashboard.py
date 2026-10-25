import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "scripts" / "build_dashboard.py"


class DashboardBuilderTest(unittest.TestCase):
    def test_builds_dashboard_data_from_archive_and_active_drafts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            archive = tmp_path / "archive"
            archive.mkdir()
            (archive / "POSTS.md").write_text(
                "# LinkedIn post archive index\n\n"
                "## 2026-10-25T13:38:01+00:00\n\n"
                "- Hook: Too many agents. Use one.\n"
                "- LinkedIn URN: `urn:li:share:7520116456903077888`\n"
                "- Topic: Anthropic single-agent loop\n\n"
                "## 2026-09-09T15:38:25+00:00\n\n"
                "- Hook: Older post.\n"
                "- LinkedIn URN: `urn:li:share:older`\n"
                "- Topic: Old topic\n"
            )
            active = tmp_path / "ACTIVE.md"
            active.write_text("1. [[anthropic-single-agent-loop]] — `posted`; verified.\n")
            out = tmp_path / "data.json"

            result = subprocess.run(
                [sys.executable, str(BUILD), "--archive", str(archive), "--active", str(active), "--out", str(out)],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(out.read_text())
            self.assertEqual(data["analytics"]["status"], "not_connected")
            self.assertEqual(data["latest_posts"][0]["hook"], "Too many agents. Use one.")
            self.assertEqual(data["latest_posts"][0]["urn"], "urn:li:share:7520116456903077888")
            self.assertEqual(data["active_items"][0]["title"], "anthropic-single-agent-loop")
            self.assertTrue(any(source["name"] == "Data Secrets" for source in data["sources"]))
            self.assertTrue(any(job["name"] == "AI News Desk" for job in data["queues"]))

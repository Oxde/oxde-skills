import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "linkedin" / "apps" / "linkedin-dashboard" / "public"


class DockerfileTest(unittest.TestCase):
    def test_dockerfile_starts_feed_service(self):
        text = (ROOT / "linkedin" / "Dockerfile").read_text()
        self.assertIn('CMD ["python", "-m", "feed.service"]', text)
        self.assertIn("COPY feed /app/feed", text)
        self.assertIn("FEED_DB=/data/feed.db", text)
        self.assertIn("FEED_STATIC=/app/public", text)

    def test_deploy_script_stages_feed_and_public(self):
        text = (ROOT / "feed" / "deploy.sh").read_text()
        for needle in ("railway up --service", "linkedin/Dockerfile", "feed/", "public/", "RAILWAY_TOKEN"):
            self.assertIn(needle, text)

    def test_collect_toml_runs_collect_on_a_schedule(self):
        text = (ROOT / "linkedin" / "railway.collect.toml").read_text()
        self.assertIn('startCommand = "python -m feed.collect"', text)
        self.assertIn('cronSchedule = "0 7,13 * * *"', text)
        self.assertIn('restartPolicyType = "NEVER"', text)
        self.assertIn("--collect", (ROOT / "feed" / "deploy.sh").read_text())

    def test_railway_toml_points_at_health_and_root_dockerfile(self):
        text = (ROOT / "linkedin" / "railway.toml").read_text()
        self.assertIn('healthcheckPath = "/api/health"', text)
        self.assertIn('dockerfilePath = "Dockerfile"', text)


class DashboardTest(unittest.TestCase):
    def test_index_includes_feed_js_and_feed_card(self):
        text = (PUBLIC / "index.html").read_text()
        self.assertIn('src="./feed.js"', text)
        self.assertIn('id="feed-stats"', text)
        self.assertIn('id="feed-items"', text)
        self.assertIn('id="feed-token"', text)

    def test_feed_js_hides_sections_on_missing_data_json(self):
        js = (PUBLIC / "feed.js").read_text()
        self.assertIn("feed_token", js)
        self.assertIn("/api/stats?days=7", js)
        self.assertIn("/api/items?status=offered,shown,picked", js)
        self.assertIn("r.status===404", js.replace(" ", ""))
        self.assertIn("Authorization", js)
        self.assertIn("safeUrl(i.url)", js)
        self.assertIn("p.protocol === 'http:' || p.protocol === 'https:'", js)
        self.assertIn("24", js)  # stale producer threshold in hours


if __name__ == "__main__":
    unittest.main()

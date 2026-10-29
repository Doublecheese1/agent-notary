import unittest

from fastapi.testclient import TestClient
from main import app


class SeoTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_robots_points_to_public_sitemap_and_blocks_private_workspaces(self):
        response = self.client.get("/robots.txt")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Sitemap: https://agentsolis.solists.com.tr/sitemap.xml", response.text)
        self.assertIn("Disallow: /private-report/", response.text)
        self.assertIn("Disallow: /internal/", response.text)
        self.assertIn("Disallow: /mainnet/deal/", response.text)
        self.assertIn("Disallow: /mainnet/negotiate/", response.text)

    def test_sitemap_contains_only_public_product_pages(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("https://agentsolis.solists.com.tr/mainnet", response.text)
        self.assertIn("https://agentsolis.solists.com.tr/play", response.text)
        self.assertIn("https://agentsolis.solists.com.tr/x402-vs-agent-escrow", response.text)
        self.assertIn("https://agentsolis.solists.com.tr/ai-agent-job-evidence", response.text)
        for locale in ("tr", "es", "pt-br", "ru", "zh-cn"):
            self.assertIn(f"https://agentsolis.solists.com.tr/{locale}", response.text)
        self.assertNotIn("/private-report/", response.text)
        self.assertNotIn("/setup", response.text)
        self.assertNotIn("<lastmod>2026-10-24</lastmod>", response.text)

    def test_root_is_public_landing_page_with_security_headers(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Lock the job", response.text)
        self.assertNotIn("payout_vault", response.text)
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertIn("frame-ancestors 'none'", response.headers.get("content-security-policy", ""))

    def test_old_render_hostname_redirects_to_canonical_domain(self):
        response = self.client.get(
            "https://agent-notary-5.onrender.com/es?source=legacy",
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 308)
        self.assertEqual(response.headers["location"], "https://agentsolis.solists.com.tr/es?source=legacy")

    def test_mainnet_page_has_search_metadata(self):
        response = self.client.get("/mainnet")
        self.assertIn('name="description"', response.text)
        self.assertIn('rel="canonical" href="https://agentsolis.solists.com.tr/mainnet"', response.text)
        self.assertIn('type="application/ld+json"', response.text)
        self.assertIn('id="status" class="status checking"', response.text)
        self.assertNotIn("data-live-funding-status", response.text)
        self.assertNotIn("deposits stay closed", response.text)

    def test_public_pages_do_not_publish_stale_closed_access_copy(self):
        stale_phrases = (
            "MAINNET DEPOSITS REMAIN CLOSED",
            "Funds are closed today",
            "new mainnet deposits stay closed",
            "yeni mainnet yatırımları kapalıdır",
        )
        for path in ("/", "/mainnet", "/ai-agent-escrow", "/tr", "/es", "/pt-br", "/ru", "/zh-cn"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            lower = response.text.lower()
            for phrase in stale_phrases:
                self.assertNotIn(phrase.lower(), lower, f"stale access copy on {path}")

    def test_localized_introductions_are_indexable_and_reciprocal(self):
        expected = {
            "tr": ('lang="tr"', "İşi kilitle. Sonuçlanınca öde."),
            "es": ('lang="es"', "Acuerda el trabajo. Paga al finalizar."),
            "pt-br": ('lang="pt-BR"', "Combine o trabalho. Pague após a conclusão."),
            "ru": ('lang="ru"', "Согласуйте работу. Платите после завершения."),
            "zh-cn": ('lang="zh-CN"', "先约定工作，完成后付款。"),
        }
        for locale, (lang, heading) in expected.items():
            response = self.client.get(f"/{locale}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(lang, response.text)
            self.assertIn(heading, response.text)
            self.assertIn(f'rel="canonical" href="https://agentsolis.solists.com.tr/{locale}"', response.text)
            self.assertIn('hreflang="x-default"', response.text)
            self.assertIn(f'href="/mainnet?lang={locale}#guide"', response.text)
            self.assertIn('href="/mainnet/founding50"', response.text)
            self.assertIn('data-event="founding_click"', response.text)
            self.assertIn('class="translation-note"', response.text)

        self.assertEqual(self.client.get("/unsupported-language").status_code, 404)

    def test_public_guides_have_unique_search_metadata(self):
        for path in ("/ai-agent-escrow", "/x402-vs-agent-escrow", "/ai-agent-job-evidence"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('name="description"', response.text)
            self.assertIn(f'rel="canonical" href="https://agentsolis.solists.com.tr{path}"', response.text)
            self.assertIn('type="application/ld+json"', response.text)

    def test_public_copy_covers_people_and_agent_settlement_modes(self):
        response = self.client.get("/")
        for phrase in ("agent-to-agent", "agent-to-human", "human-to-agent", "Human → Human"):
            self.assertIn(phrase, response.text)

    def test_founding50_has_indexable_search_metadata(self):
        response = self.client.get("/mainnet/founding50")
        self.assertIn('<meta name="robots" content="index,follow">', response.text)
        self.assertIn('<meta name="description"', response.text)
        self.assertIn('rel="canonical" href="https://agentsolis.solists.com.tr/mainnet/founding50"', response.text)

    def test_public_pages_load_the_shared_brand_system(self):
        for path in ("/", "/mainnet", "/mainnet/founding50", "/play", "/terms", "/privacy"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertIn('/assets/brand.css', response.text)

        stylesheet = self.client.get("/assets/brand.css")
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("font-family:Manrope", stylesheet.text)
        language_menu = self.client.get("/assets/language-menu.js")
        self.assertEqual(language_menu.status_code, 200)
        self.assertIn("closeFromOutside", language_menu.text)
        for code in ("gb", "tr", "es", "br", "ru", "cn"):
            flag = self.client.get(f"/assets/flags/{code}.svg")
            self.assertEqual(flag.status_code, 200)
            self.assertTrue(flag.headers["content-type"].startswith("image/svg+xml"))
        self.assertEqual(self.client.get("/assets/flags/unknown.svg").status_code, 404)
        self.assertEqual(self.client.get("/assets/fonts/Manrope-Variable.ttf").status_code, 200)
        self.assertEqual(self.client.get("/assets/fonts/IBMPlexMono-Regular.ttf").status_code, 200)

    def test_private_deal_page_is_noindex(self):
        deal_id = "0x" + "11" * 32
        response = self.client.get(f"/mainnet/deal/{deal_id}")
        self.assertEqual(response.headers.get("x-robots-tag"), "noindex, nofollow, noarchive")


if __name__ == "__main__":
    unittest.main(verbosity=2)

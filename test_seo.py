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
        self.assertIn("Sitemap: https://agent-notary-5.onrender.com/sitemap.xml", response.text)
        self.assertIn("Disallow: /reports", response.text)
        self.assertIn("Disallow: /mainnet/deal/", response.text)
        self.assertIn("Disallow: /mainnet/negotiate/", response.text)

    def test_sitemap_contains_only_public_product_pages(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertIn("https://agent-notary-5.onrender.com/mainnet", response.text)
        self.assertIn("https://agent-notary-5.onrender.com/play", response.text)
        self.assertNotIn("/reports", response.text)
        self.assertNotIn("/setup", response.text)

    def test_mainnet_page_has_search_metadata(self):
        response = self.client.get("/mainnet")
        self.assertIn('name="description"', response.text)
        self.assertIn('rel="canonical" href="https://agent-notary-5.onrender.com/mainnet"', response.text)
        self.assertIn('type="application/ld+json"', response.text)

    def test_private_deal_page_is_noindex(self):
        deal_id = "0x" + "11" * 32
        response = self.client.get(f"/mainnet/deal/{deal_id}")
        self.assertEqual(response.headers.get("x-robots-tag"), "noindex, nofollow, noarchive")


if __name__ == "__main__":
    unittest.main(verbosity=2)

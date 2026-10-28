"""Check that public language pages contain the full landing journey."""
import unittest
from html.parser import HTMLParser
from pathlib import Path

from international import LOCALES, localized_landing


class SectionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = 0

    def handle_starttag(self, tag, attrs):
        if tag == "section":
            self.sections += 1


class LocalizedLandingParityTests(unittest.TestCase):
    def test_nine_sections_match_english_landing(self):
        english = Path(__file__).with_name("static").joinpath("index.html").read_text(encoding="utf-8")
        parser = SectionParser()
        parser.feed(english)
        self.assertEqual(parser.sections, 9)
        for locale in LOCALES:
            with self.subTest(locale=locale):
                html = localized_landing(locale)
                translated = SectionParser()
                translated.feed(html)
                self.assertEqual(translated.sections, parser.sections)
                self.assertIn('id="videos"', html)
                self.assertIn('id="explainerVideo"', html)
                self.assertIn('id="who-can-use"', html)
                self.assertIn('data-live-mainnet-status', html)
                self.assertIn('105.00 USDC', html)
                self.assertIn('98.50 USDC', html)
                self.assertIn('50 USDC', html)
                self.assertEqual(html.count('data-video-chapter='), 5)
                self.assertIn(f'01.{locale}.vtt', html)


if __name__ == "__main__":
    unittest.main()

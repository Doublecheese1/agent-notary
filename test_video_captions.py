import unittest

from fastapi.testclient import TestClient

from main import app
from scripts.build_video_captions import CAPTIONS, TIMES


class VideoCaptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_all_languages_have_timed_captions_for_each_video(self):
        for language, chapters in CAPTIONS.items():
            self.assertEqual(set(chapters), set(TIMES))
            for chapter, captions in chapters.items():
                with self.subTest(language=language, chapter=chapter):
                    response = self.client.get(f"/assets/videos/{chapter}.{language}.vtt")
                    self.assertEqual(response.status_code, 200)
                    self.assertTrue(response.headers["content-type"].startswith("text/vtt"))
                    self.assertEqual(response.text.splitlines()[0], "WEBVTT")
                    self.assertEqual(response.text.count(" --> "), len(captions))
                    self.assertEqual(len(captions), len(TIMES[chapter]))

    def test_localized_pages_link_to_shared_videos_and_language(self):
        for language in ("tr", "es", "pt-br", "ru", "zh-cn"):
            response = self.client.get(f"/{language}")
            self.assertEqual(response.status_code, 200)
            for chapter in TIMES:
                self.assertIn(f"/?lang={language}&amp;video={chapter}#videos", response.text)

    def test_only_listed_caption_files_are_served(self):
        for filename in ("01.xx.vtt", "../main.py", "06.tr.vtt"):
            self.assertEqual(self.client.get(f"/assets/videos/{filename}").status_code, 404)


if __name__ == "__main__":
    unittest.main()

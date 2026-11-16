"""Interview links: the two accepted YouTube formats."""
from django.test import SimpleTestCase

from family.youtube import embed_url, extract_video_id, watch_url


class ExtractVideoIdTests(SimpleTestCase):
    def test_watch_format(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ"
        )

    def test_watch_format_without_www(self):
        self.assertEqual(
            extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ"), "dQw4w9WgXcQ"
        )

    def test_watch_format_with_other_parameters(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=42s"),
            "dQw4w9WgXcQ",
        )

    def test_short_format(self):
        self.assertEqual(extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_short_format_with_share_parameter(self):
        self.assertEqual(
            extract_video_id("https://youtu.be/dQw4w9WgXcQ?si=abcDEF123"), "dQw4w9WgXcQ"
        )

    def test_code_with_dash_and_underscore(self):
        self.assertEqual(extract_video_id("https://youtu.be/a-b_c-d_e-f"), "a-b_c-d_e-f")

    def test_other_sites_are_not_accepted(self):
        for url in (
            "https://vimeo.com/123456",
            "https://example.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/channel/abc",
            "https://www.youtube.com/watch?v=short",
            "https://youtu.be/",
            "not a link",
            "",
        ):
            with self.subTest(url=url):
                self.assertIsNone(extract_video_id(url))


class PlayerAddressTests(SimpleTestCase):
    def test_embedded_player_uses_the_address_without_cookies(self):
        self.assertEqual(
            embed_url("dQw4w9WgXcQ"), "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"
        )

    def test_link_to_a_moment_of_the_video(self):
        self.assertEqual(
            watch_url("dQw4w9WgXcQ", start=252),
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=252s",
        )

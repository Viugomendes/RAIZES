"""Smaller copies of the photos: the originals never go to the site."""
import io
import tempfile
from pathlib import Path

from django.test import SimpleTestCase, TestCase, override_settings
from PIL import Image

from family.images import (
    AVATAR,
    LARGE,
    THUMB,
    VariantError,
    make_variant,
    variant_url,
)
from family.models import Clip


def save_image(path: Path, size=(3000, 2000), exif_gps=False, orientation=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", size, (200, 120, 60))
    exif = Image.Exif()
    if exif_gps:
        exif[0x8825] = {1: "S", 2: (23.0, 33.0, 0.0)}  # GPS block
        exif[0x010F] = "Camera Maker"
    if orientation:
        exif[0x0112] = orientation
    image.save(path, format="JPEG", exif=exif.tobytes())


class VariantTestCase(SimpleTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.media = Path(folder.name) / "media"
        self.cache = Path(folder.name) / "cache"
        overrides = override_settings(MEDIA_ROOT=self.media, RAIZES_CACHE_DIR=self.cache)
        overrides.enable()
        self.addCleanup(overrides.disable)


class MakeVariantTests(VariantTestCase):
    def test_large_photo_is_reduced_to_the_width_asked(self):
        save_image(self.media / "photos" / "big.jpg")

        result = Image.open(make_variant("photos/big.jpg", THUMB))

        self.assertEqual(max(result.size), THUMB)
        self.assertEqual(result.format, "JPEG")

    def test_proportions_are_kept(self):
        save_image(self.media / "photos" / "big.jpg", size=(3000, 1500))

        result = Image.open(make_variant("photos/big.jpg", THUMB))

        self.assertEqual(result.size, (THUMB, THUMB // 2))

    def test_small_photo_is_never_enlarged(self):
        save_image(self.media / "photos" / "small.jpg", size=(300, 200))

        result = Image.open(make_variant("photos/small.jpg", LARGE))

        self.assertEqual(result.size, (300, 200))

    def test_hidden_data_of_the_file_is_removed(self):
        save_image(self.media / "photos" / "gps.jpg", exif_gps=True)

        result = Image.open(make_variant("photos/gps.jpg", THUMB))

        self.assertEqual(dict(result.getexif()), {})

    def test_photo_taken_sideways_is_turned_upright(self):
        save_image(self.media / "photos" / "side.jpg", size=(400, 200), orientation=6)

        result = Image.open(make_variant("photos/side.jpg", LARGE))

        self.assertEqual(result.size, (200, 400))

    def test_png_with_transparency_becomes_jpeg_on_white(self):
        path = self.media / "people" / "a.png"
        path.parent.mkdir(parents=True)
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(path)

        result = Image.open(make_variant("people/a.png", AVATAR))

        self.assertEqual(result.mode, "RGB")
        self.assertEqual(result.getpixel((10, 10)), (255, 255, 255))

    def test_second_request_uses_the_copy_already_made(self):
        save_image(self.media / "photos" / "big.jpg")
        first = make_variant("photos/big.jpg", THUMB)
        modified = first.stat().st_mtime_ns

        second = make_variant("photos/big.jpg", THUMB)

        self.assertEqual(first, second)
        self.assertEqual(second.stat().st_mtime_ns, modified)

    def test_replaced_original_gives_a_new_copy(self):
        path = self.media / "photos" / "big.jpg"
        save_image(path, size=(800, 600))
        make_variant("photos/big.jpg", LARGE)
        save_image(path, size=(600, 800))

        result = Image.open(make_variant("photos/big.jpg", LARGE))

        self.assertEqual(result.size, (600, 800))

    def test_unknown_width_is_refused(self):
        save_image(self.media / "photos" / "big.jpg")

        with self.assertRaises(VariantError):
            make_variant("photos/big.jpg", 123)

    def test_path_outside_the_media_folder_is_refused(self):
        for name in ("../secret.jpg", "/etc/passwd", "photos/../../x.jpg"):
            with self.subTest(name=name), self.assertRaises(VariantError):
                make_variant(name, THUMB)

    def test_missing_file_is_refused(self):
        with self.assertRaises(VariantError):
            make_variant("photos/none.jpg", THUMB)

    def test_file_that_is_not_an_image_is_refused(self):
        path = self.media / "photos" / "fake.jpg"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"not an image")

        with self.assertRaises(VariantError):
            make_variant("photos/fake.jpg", THUMB)


class VariantUrlTests(SimpleTestCase):
    def test_address_of_a_copy(self):
        self.assertEqual(variant_url("photos/big.png", THUMB), f"/media/v/{THUMB}/photos/big.png.jpg")

    def test_empty_file_has_no_address(self):
        self.assertEqual(variant_url("", THUMB), "")


class VariantViewTests(VariantTestCase, TestCase):
    def test_copy_is_served_while_working_locally(self):
        save_image(self.media / "photos" / "big.jpg")

        response = self.client.get(f"/media/v/{THUMB}/photos/big.jpg.jpg")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/jpeg")
        image = Image.open(io.BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(max(image.size), THUMB)

    def test_unknown_copy_is_a_404(self):
        self.assertEqual(self.client.get(f"/media/v/{THUMB}/photos/none.jpg.jpg").status_code, 404)
        self.assertEqual(self.client.get("/media/v/123/photos/none.jpg.jpg").status_code, 404)

    def test_originals_are_not_served(self):
        save_image(self.media / "photos" / "big.jpg")

        self.assertEqual(self.client.get("/media/photos/big.jpg").status_code, 404)


class ClipViewTests(VariantTestCase, TestCase):
    def setUp(self):
        super().setUp()
        save_image(self.media / "people" / "lia.png", exif_gps=True)
        clip = self.media / "clips" / "conversa.mp3"
        clip.parent.mkdir(parents=True, exist_ok=True)
        clip.write_bytes(b"ID3 not really a song")
        Clip.objects.create(file="clips/conversa.mp3")

    def test_a_clip_is_served(self):
        response = self.client.get("/media/clips/conversa.mp3")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"ID3 not really a song")

    def test_other_files_of_the_media_folder_are_never_served(self):
        for path in (
            "/media/clips/%2e%2e/people/lia.png",
            "/media/clips/%2E%2E/people/lia.png",
            "/media/clips/../people/lia.png",
            "/media/clips/./conversa.mp3",
            "/media/clips/%2e/conversa.mp3",
            "/media/clips/sub/../conversa.mp3",
            "/media/clips/..%2fpeople/lia.png",
            "/media/clips/..%5cpeople%5clia.png",
        ):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_a_file_in_the_clips_folder_unknown_to_the_database_is_a_404(self):
        (self.media / "clips" / "esquecido.mp3").write_bytes(b"x")

        self.assertEqual(self.client.get("/media/clips/esquecido.mp3").status_code, 404)

"""Problems found by the second independent review, each with its test."""
import json
import tempfile
from pathlib import Path

from django.conf import settings
from django.test import TestCase, override_settings
from PIL import Image

from family.export import ExportError, export_site, find_dead_links
from family.images import THUMB, make_variant
from family.models import Person, Photo, Recipe
from family.site_data import build_site_data

from .base import DemoFamilyTestCase, IsolatedFilesMixin
from .test_images import VariantTestCase


class OutputFolderMixin:
    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.output = Path(folder.name) / "dist"


class EmptyFamilyExportTests(OutputFolderMixin, IsolatedFilesMixin, TestCase):
    def test_family_with_nobody_yet_can_be_exported(self):
        report = export_site(self.output)

        self.assertTrue((self.output / "pt-br" / "index.html").is_file())
        self.assertTrue((self.output / "pt-br" / "tree" / "index.html").is_file())
        self.assertEqual(report.pages, 2 * 5)
        self.assertEqual(find_dead_links(self.output), [])


class NoRecipesExportTests(OutputFolderMixin, DemoFamilyTestCase):
    def test_family_without_recipes_can_be_exported(self):
        Recipe.objects.all().delete()
        # Lia's text links to a recipe; without recipes that link must go too.
        Person.objects.filter(identifier="lia-carvalho-1996").update(tastes="")

        export_site(self.output)

        self.assertFalse((self.output / "pt-br" / "recipes").exists())
        self.assertTrue((self.output / "pt-br" / "people" / "lia-carvalho-1996" / "index.html").is_file())


class MediaPathTests(OutputFolderMixin, DemoFamilyTestCase):
    def test_original_photo_cannot_escape_through_a_clips_address(self):
        photo = Photo.objects.first()
        photo.caption = f"veja media/clips/../{photo.image.name}"
        photo.save()

        with self.assertRaises(ExportError):
            export_site(self.output)

        self.assertFalse((self.output / "media" / photo.image.name).exists())


class JpegCommentTests(VariantTestCase):
    def test_comment_hidden_in_a_jpeg_is_removed(self):
        path = self.media / "photos" / "commented.jpg"
        path.parent.mkdir(parents=True)
        Image.new("RGB", (900, 600), (10, 20, 30)).save(path, comment=b"GPS: home of grandma")

        copy = make_variant("photos/commented.jpg", THUMB)

        self.assertNotIn(b"grandma", copy.read_bytes())
        self.assertNotIn("comment", Image.open(copy).info)


class HiddenSectionPhrasesTests(DemoFamilyTestCase):
    @override_settings(RAIZES_HIDDEN_SECTIONS={"legacy"})
    def test_quotes_of_hidden_sections_never_reach_the_browser(self):
        phrases = [phrase["text"] for phrase in build_site_data()["phrases"]]

        self.assertFalse(any("Guardem as histórias" in text for text in phrases))

    def test_quotes_of_visible_sections_are_used(self):
        phrases = [phrase["text"] for phrase in build_site_data()["phrases"]]

        self.assertTrue(any("Guardem as histórias" in text for text in phrases))


class DeceasedPlacesTests(DemoFamilyTestCase):
    def test_a_deceased_person_does_not_live_anywhere_on_the_map(self):
        person = Person.objects.get(identifier="anselmo-figueira-1940")
        person.lives_in = person.birth_place
        person.save()

        data = {p["id"]: p for p in build_site_data()["people"]}

        self.assertIsNone(data["anselmo-figueira-1940"]["livesIn"])


class NewOnTheSiteHistoryTests(OutputFolderMixin, DemoFamilyTestCase):
    def setUp(self):
        super().setUp()
        Path(settings.RAIZES_HISTORY_FILE).unlink(missing_ok=True)

    def news_keys(self):
        return {(item["type"], item["key"]) for item in build_site_data()["news"]}

    def test_the_first_publication_does_not_call_everybody_new(self):
        with override_settings(RAIZES_EXPORT_DIR=self.output):
            export_site()

        self.assertEqual(self.news_keys(), set())

    def test_people_added_after_a_publication_are_new(self):
        with override_settings(RAIZES_EXPORT_DIR=self.output):
            export_site()
            newcomer = Person(given_name="Bruno", surname="Pereira", birth_date="2025")
            newcomer.full_clean()
            newcomer.save()

            self.assertIn(("person", newcomer.identifier), self.news_keys())
            export_site()

        self.assertIn(("person", newcomer.identifier), self.news_keys())
        self.assertNotIn(("person", "lia-carvalho-1996"), self.news_keys())

    def test_an_export_to_another_folder_is_not_a_publication(self):
        export_site(self.output)

        self.assertFalse(Path(settings.RAIZES_HISTORY_FILE).exists())

    def test_history_stores_the_publications(self):
        with override_settings(RAIZES_EXPORT_DIR=self.output):
            export_site()

        history = json.loads(Path(settings.RAIZES_HISTORY_FILE).read_text())
        self.assertIn("person:lia-carvalho-1996", history["first_seen"])
        self.assertEqual(len(history["publications"]), 1)


class TreeLinesTests(DemoFamilyTestCase):
    def test_child_lines_end_at_the_centre_of_the_circle(self):
        # The circles are drawn over the lines, so a line that ends at the
        # centre still fits when "see from..." changes the size of a circle.
        import re

        page = self.client.get("/pt-br/tree/").content.decode()
        html = re.search(r'<svg id="family-tree".*?</svg>', page, re.DOTALL).group(0)
        centres = {
            float(cy)
            for cy in re.findall(r'<circle class="dot" cx="[^"]+" cy="([^"]+)"', html)
        }
        ends = [float(match) for match in re.findall(r'<path class="child-line [a-z]+" d="[^"]*,([\d.-]+)"', html)]

        self.assertTrue(ends)
        for end in ends:
            self.assertTrue(any(abs(end - centre) < 0.11 for centre in centres), end)

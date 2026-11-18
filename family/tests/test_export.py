"""The static export: the whole site as files that open without Django."""
import json
import re
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import translation

from family.export import ExportError, export_site, find_dead_links
from family.models import Clip, Person, Photo, Recipe

from .test_demo import DemoFamilyTestCase


def expected_pages() -> int:
    """Two languages x (news, tree, map, search, who is this, people, recipes)."""
    return 2 * (5 + Person.objects.count() + Recipe.objects.count())


class ExportTestCase(DemoFamilyTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.output = Path(folder.name) / "dist"

    def read(self, relative_path: str) -> str:
        return (self.output / relative_path).read_text(encoding="utf-8")


class ExportedFilesTests(DemoFamilyTestCase):
    """These tests only read the result, so the site is exported once for all."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.folder = tempfile.TemporaryDirectory()
        cls.output = Path(cls.folder.name) / "dist"
        cls.report = export_site(cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()
        super().tearDownClass()

    def read(self, relative_path: str) -> str:
        return (self.output / relative_path).read_text(encoding="utf-8")

    def test_every_page_of_the_plan_in_both_languages(self):
        for page in ("index.html", "tree/index.html", "tree/map/index.html", "search/index.html", "photos/who/index.html"):
            for path in (f"pt-br/{page}", f"es/{page}"):
                with self.subTest(path=path):
                    self.assertTrue((self.output / path).is_file())

    def test_data_for_the_browser_is_exported_once(self):
        script = self.read("data/family.js")

        self.assertTrue(script.startswith("window.RAIZES_DATA = {"))
        self.assertIn("lia-carvalho-1996", script)

    def test_one_page_per_recipe(self):
        for slug in Recipe.objects.values_list("slug", flat=True):
            with self.subTest(recipe=slug):
                self.assertTrue((self.output / "es" / "recipes" / slug / "index.html").is_file())

    def test_one_page_per_person_in_each_language(self):
        for identifier in Person.objects.values_list("identifier", flat=True):
            for language in ("pt-br", "es"):
                with self.subTest(person=identifier, language=language):
                    self.assertTrue(
                        (self.output / language / "people" / identifier / "index.html").is_file()
                    )

    def test_report_counts_the_pages(self):
        self.assertEqual(self.report.pages, expected_pages())

    def test_front_door_sends_the_visitor_to_the_default_language(self):
        html = self.read("index.html")

        self.assertIn('http-equiv="refresh"', html)
        self.assertIn("url=pt-br/index.html", html)
        self.assertIn('href="pt-br/index.html"', html)

    def test_pages_are_in_the_right_language(self):
        self.assertIn("Árvore da família", self.read("pt-br/tree/index.html"))
        self.assertIn("Árbol de la familia", self.read("es/tree/index.html"))
        self.assertIn("<h1>Novidades</h1>", self.read("pt-br/index.html"))

    def test_css_javascript_and_icon_are_copied(self):
        for path in (
            "static/css/site.css",
            "static/js/tree.js",
            "static/js/mural.js",
            "static/js/carousel.js",
            "static/js/search.js",
            "static/vendor/leaflet/leaflet.js",
            "static/vendor/leaflet/leaflet.css",
            "static/icons/favicon.svg",
        ):
            with self.subTest(path=path):
                self.assertTrue((self.output / path).is_file())

    def test_admin_panel_is_not_exported(self):
        self.assertFalse((self.output / "admin").exists())
        self.assertFalse((self.output / "static" / "admin").exists())

    def test_search_engines_are_asked_to_stay_away(self):
        self.assertIn("Disallow: /", self.read("robots.txt"))
        self.assertIn('content="noindex, nofollow"', self.read("pt-br/index.html"))

    def test_no_link_starts_at_the_root_of_a_server(self):
        for page in self.output.rglob("*.html"):
            html = page.read_text(encoding="utf-8")
            with self.subTest(page=str(page.relative_to(self.output))):
                self.assertEqual(re.findall(r'(?:href|src|data-root)="/[^"]*"', html), [])

    def test_scripts_know_where_the_root_of_the_site_is(self):
        self.assertIn('data-root="../index.html"', self.read("pt-br/index.html"))
        self.assertIn('data-root="../../../index.html"', self.read("pt-br/people/lia-carvalho-1996/index.html"))

    def test_every_link_leads_to_a_file_that_exists(self):
        self.assertEqual(find_dead_links(self.output), [])

    def test_tree_links_to_the_page_of_a_person(self):
        self.assertIn('href="../people/lia-carvalho-1996/index.html"', self.read("pt-br/tree/index.html"))

    def test_person_page_links_back_and_to_the_other_language(self):
        html = self.read("pt-br/people/lia-carvalho-1996/index.html")

        self.assertIn('href="../../index.html"', html)
        self.assertIn('href="../../../es/people/lia-carvalho-1996/index.html"', html)
        self.assertIn('href="../bento-carvalho-1993/index.html"', html)
        self.assertIn('href="../../../static/css/site.css"', html)

    def test_search_in_place_finds_its_scripts_in_the_exported_site(self):
        html = self.read("es/people/lia-carvalho-1996/index.html")

        self.assertIn('<script src="../../../data/family.js" data-provides="RAIZES_DATA">', html)
        self.assertIn('<script src="../../../static/js/search.js" data-provides="RaizesSearch">', html)
        self.assertIn('class="nav-search" href="../../search/index.html"', html)
        self.assertIn('data-root="../../../index.html"', html)

    def test_links_to_other_sites_are_untouched(self):
        html = self.read("pt-br/people/helena-figueira-1970/index.html")

        self.assertIn('src="https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"', html)
        self.assertIn('href="https://www.youtube.com/watch?v=aqz-KE-bpKQ&amp;t=42s"', html)



class ExportLanguageTests(ExportTestCase):
    def test_active_language_is_restored_after_the_export(self):
        with translation.override("es"):
            export_site(self.output)

            self.assertEqual(translation.get_language(), "es")


class ExportedMediaTests(ExportTestCase):
    def test_only_small_copies_of_the_photos_in_use_are_exported(self):
        media = Path(settings.MEDIA_ROOT)
        (media / "people" / "not-used-anywhere.png").write_bytes(b"private")
        (media / "originals").mkdir(exist_ok=True)
        (media / "originals" / "scan.tiff").write_bytes(b"private")

        export_site(self.output)

        exported = [path for path in (self.output / "media").rglob("*") if path.is_file()]
        names = {path.relative_to(self.output / "media").as_posix() for path in exported}
        for photo in Photo.objects.all():
            with self.subTest(photo=photo.caption):
                self.assertIn(f"v/480/{photo.image.name}.jpg", names)
                self.assertIn(f"v/1600/{photo.image.name}.jpg", names)
                self.assertNotIn(photo.image.name, names)
        self.assertIn("v/320/people/lia-carvalho-1996.png.jpg", names)
        self.assertIn("v/128/people/lia-carvalho-1996.png.jpg", names)
        self.assertNotIn("people/lia-carvalho-1996.png", names)
        self.assertFalse(any("not-used-anywhere" in name or "scan.tiff" in name for name in names))
        self.assertTrue(all(name.startswith(("v/", "clips/")) for name in names))
        self.assertEqual(find_dead_links(self.output), [])

    def test_recordings_are_copied_as_they_are(self):
        export_site(self.output)

        clip = Clip.objects.get()
        copied = self.output / "media" / clip.file.name
        self.assertEqual(copied.read_bytes(), (Path(settings.MEDIA_ROOT) / clip.file.name).read_bytes())

    def test_missing_original_stops_the_export_with_a_clear_message(self):
        photo = Photo.objects.first()
        original = Path(settings.MEDIA_ROOT) / photo.image.name
        # The files are shared by the tests of this class: put it back afterwards.
        saved = original.read_bytes()
        self.addCleanup(original.write_bytes, saved)
        original.unlink()

        with self.assertRaises(ExportError) as caught:
            export_site(self.output)

        self.assertTrue(any(photo.image.name in problem for problem in caught.exception.problems))


class ExportSafetyTests(ExportTestCase):
    def break_a_link(self):
        lia = Person.objects.get(identifier="lia-carvalho-1996")
        lia.work = "Trabalhei com [[ninguem-silva-1900]]."
        lia.save()

    def test_broken_link_stops_the_export_and_says_where_it_is(self):
        self.break_a_link()

        with self.assertRaises(ExportError) as caught:
            export_site(self.output)

        self.assertEqual(len(caught.exception.problems), 1)
        self.assertIn("Lia Figueira Carvalho", caught.exception.problems[0])
        self.assertIn("[[ninguem-silva-1900]]", caught.exception.problems[0])
        self.assertFalse(self.output.exists())

    def test_broken_link_leaves_the_previous_export_untouched(self):
        export_site(self.output)
        before = self.read("pt-br/people/lia-carvalho-1996/index.html")
        self.break_a_link()

        with self.assertRaises(ExportError):
            export_site(self.output)

        self.assertEqual(self.read("pt-br/people/lia-carvalho-1996/index.html"), before)

    def test_folder_that_was_not_created_by_the_export_is_never_erased(self):
        self.output.mkdir()
        (self.output / "family-photos.txt").write_text("precious")

        with self.assertRaises(ExportError):
            export_site(self.output)

        self.assertEqual((self.output / "family-photos.txt").read_text(), "precious")
        self.assertFalse((self.output / "pt-br").exists())

    def test_empty_folder_is_accepted(self):
        self.output.mkdir()

        export_site(self.output)

        self.assertTrue((self.output / "pt-br" / "index.html").is_file())

    def test_exporting_again_replaces_the_previous_export(self):
        export_site(self.output)
        Person.objects.get(identifier="sofia-ipe-2006").delete()

        export_site(self.output)

        self.assertFalse((self.output / "pt-br" / "people" / "sofia-ipe-2006").exists())
        self.assertTrue((self.output / "pt-br" / "people" / "lia-carvalho-1996").exists())
        self.assertEqual(find_dead_links(self.output), [])

    def test_dead_link_checker_finds_a_missing_page(self):
        export_site(self.output)
        (self.output / "pt-br" / "people" / "bento-carvalho-1993" / "index.html").unlink()

        dead = find_dead_links(self.output)

        self.assertTrue(dead)
        self.assertTrue(all("bento-carvalho-1993" in problem for problem in dead))


class ExportCommandTests(ExportTestCase):
    def test_command_exports_and_says_what_it_did(self):
        output = StringIO()

        call_command("export_site", output=str(self.output), stdout=output)

        self.assertTrue((self.output / "index.html").is_file())
        self.assertIn(str(expected_pages()), output.getvalue())
        self.assertIn("index.html", output.getvalue())

    def test_command_lists_the_broken_links(self):
        lia = Person.objects.get(identifier="lia-carvalho-1996")
        lia.work = "Trabalhei com [[ninguem-silva-1900]]."
        lia.save()

        with self.assertRaises(CommandError) as caught:
            call_command("export_site", output=str(self.output), stdout=StringIO())

        self.assertIn("[[ninguem-silva-1900]]", str(caught.exception))
        self.assertFalse(self.output.exists())

    def test_default_export_folder_is_dist(self):
        self.assertEqual(Path(settings.RAIZES_EXPORT_DIR), Path(settings.BASE_DIR) / "dist")

    def test_hidden_and_backup_files_in_static_are_not_exported(self):
        static_dir = Path(settings.BASE_DIR) / "static"
        strays = [static_dir / ".raizes-test-hidden", static_dir / "css" / "site.css~"]
        for stray in strays:
            stray.write_text("stray")
            self.addCleanup(stray.unlink)

        export_site(self.output)

        self.assertFalse((self.output / "static" / ".raizes-test-hidden").exists())
        self.assertFalse((self.output / "static" / "css" / "site.css~").exists())

    def test_command_uses_the_configured_export_folder(self):
        with override_settings(RAIZES_EXPORT_DIR=self.output):
            call_command("export_site", stdout=StringIO())

        self.assertTrue((self.output / "pt-br" / "index.html").is_file())

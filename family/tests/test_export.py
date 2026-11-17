"""The static export: the whole site as files that open without Django."""
import re
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import translation

from family.demo import load_demo_family
from family.export import ExportError, export_site, find_dead_links
from family.models import Person

from .test_demo import DemoFamilyTestCase


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

    def test_tree_and_people_list_in_both_languages(self):
        for path in ("pt-br/index.html", "es/index.html", "pt-br/people/index.html", "es/people/index.html"):
            with self.subTest(path=path):
                self.assertTrue((self.output / path).is_file())

    def test_one_page_per_person_in_each_language(self):
        for identifier in Person.objects.values_list("identifier", flat=True):
            for language in ("pt-br", "es"):
                with self.subTest(person=identifier, language=language):
                    self.assertTrue(
                        (self.output / language / "people" / identifier / "index.html").is_file()
                    )

    def test_report_counts_the_pages(self):
        # Two languages x (tree + list + one page per person).
        self.assertEqual(self.report.pages, 2 * (2 + Person.objects.count()))

    def test_front_door_sends_the_visitor_to_the_default_language(self):
        html = self.read("index.html")

        self.assertIn('http-equiv="refresh"', html)
        self.assertIn("url=pt-br/index.html", html)
        self.assertIn('href="pt-br/index.html"', html)

    def test_pages_are_in_the_right_language(self):
        self.assertIn("Árvore da família", self.read("pt-br/index.html"))
        self.assertIn("Árbol de la familia", self.read("es/index.html"))

    def test_css_javascript_and_icon_are_copied(self):
        for path in ("static/css/site.css", "static/js/tree.js", "static/js/person.js", "static/icons/favicon.svg"):
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
                self.assertEqual(re.findall(r'(?:href|src)="/[^"]*"', html), [])

    def test_every_link_leads_to_a_file_that_exists(self):
        self.assertEqual(find_dead_links(self.output), [])

    def test_tree_links_to_the_page_of_a_person(self):
        self.assertIn('href="people/lia-carvalho-1996/index.html"', self.read("pt-br/index.html"))

    def test_person_page_links_back_and_to_the_other_language(self):
        html = self.read("pt-br/people/lia-carvalho-1996/index.html")

        self.assertIn('href="../../index.html"', html)
        self.assertIn('href="../../../es/people/lia-carvalho-1996/index.html"', html)
        self.assertIn('href="../bento-carvalho-1993/index.html"', html)
        self.assertIn('href="../../../static/css/site.css"', html)

    def test_links_to_other_sites_are_untouched(self):
        html = self.read("pt-br/people/helena-figueira-1970/index.html")

        self.assertIn('src="https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"', html)
        self.assertIn('href="https://www.youtube.com/watch?v=aqz-KE-bpKQ&amp;t=42s"', html)



class ExportLanguageTests(ExportTestCase):
    def test_active_language_is_restored_after_the_export(self):
        with translation.override("es"):
            export_site(self.output)

            self.assertEqual(translation.get_language(), "es")


class ExportedPhotosTests(ExportTestCase):
    def test_only_the_photos_in_use_are_copied(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            load_demo_family(with_portraits=True)
            (Path(media) / "people" / "not-used-anywhere.png").write_bytes(b"private")
            (Path(media) / "originals").mkdir()
            (Path(media) / "originals" / "scan.tiff").write_bytes(b"private")

            export_site(self.output)

        copied = sorted(path.name for path in (self.output / "media").rglob("*") if path.is_file())
        with_photo = Person.objects.exclude(photo="").count()
        self.assertEqual(len(copied), with_photo)
        self.assertIn("lia-carvalho-1996.png", copied)
        self.assertNotIn("not-used-anywhere.png", copied)
        self.assertNotIn("scan.tiff", copied)
        self.assertIn(
            'src="../../../media/people/lia-carvalho-1996.png"',
            self.read("pt-br/people/lia-carvalho-1996/index.html"),
        )
        self.assertEqual(find_dead_links(self.output), [])


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
        Person.objects.get(identifier="olga-figueira-1943").parent_links.all().delete()
        Person.objects.get(identifier="olga-figueira-1943").delete()

        export_site(self.output)

        self.assertFalse((self.output / "pt-br" / "people" / "olga-figueira-1943").exists())
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
        self.assertIn(str(2 * (2 + Person.objects.count())), output.getvalue())
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

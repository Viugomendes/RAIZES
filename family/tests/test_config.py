"""Settings each family chooses in .env (section 9 of the plan)."""
from django.test import SimpleTestCase, override_settings

from config.env import parse_list

from .test_person_page import PersonPageTestCase, section


class ParsingTests(SimpleTestCase):
    def test_list_of_words(self):
        self.assertEqual(parse_list(" tastes, Legacy ,,gallery "), ["tastes", "legacy", "gallery"])
        self.assertEqual(parse_list(""), [])



class HiddenSectionsTests(PersonPageTestCase):
    @override_settings(RAIZES_HIDDEN_SECTIONS={"childhood", "gallery"})
    def test_hidden_sections_do_not_appear(self):
        html = self.page("helena-figueira-1970")

        self.assertEqual(section(html, "childhood"), "")
        self.assertEqual(section(html, "gallery"), "")
        self.assertNotEqual(section(html, "work"), "")

    def test_every_section_appears_by_default(self):
        html = self.page("helena-figueira-1970")

        self.assertNotEqual(section(html, "childhood"), "")
        self.assertNotEqual(section(html, "gallery"), "")

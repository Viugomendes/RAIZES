"""Settings each family chooses in .env (section 9 of the plan)."""
from django.test import SimpleTestCase, override_settings

from config.env import parse_colors, parse_list
from family.tree_skin import SIDE_COLORS, side_color

from .test_person_page import PersonPageTestCase, section


class ParsingTests(SimpleTestCase):
    def test_list_of_words(self):
        self.assertEqual(parse_list(" tastes, Legacy ,,gallery "), ["tastes", "legacy", "gallery"])
        self.assertEqual(parse_list(""), [])

    def test_colours(self):
        self.assertEqual(parse_colors("#112233, #AABBCC"), ["#112233", "#aabbcc"])
        self.assertEqual(parse_colors(""), [])

    def test_invalid_colour_is_refused(self):
        with self.assertRaises(ValueError):
            parse_colors("#112233, red")


class SideColoursTests(SimpleTestCase):
    def test_default_colours(self):
        self.assertEqual(side_color("a", ["a", "b"]), SIDE_COLORS[0])

    @override_settings(RAIZES_SIDE_COLORS=["#111111", "#222222"])
    def test_family_can_choose_other_colours(self):
        self.assertEqual(side_color("b", ["a", "b"]), "#222222")


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

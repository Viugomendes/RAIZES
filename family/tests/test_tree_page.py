"""The skin of the tree and the page that shows it."""
import re

from django.conf import settings
from django.test import SimpleTestCase, TestCase, override_settings

from family.kinship import ADOPTIVE, BIOLOGICAL, FOSTER
from family.models import ChildLink, Person, Union
from family.tree_skin import (
    FADES,
    PERSON_COLOR,
    RADII,
    SURFACE,
    _mix_with_white,
    child_line_class,
    node_style,
    union_line_class,
)

from .test_demo import DemoFamilyTestCase
from .test_models import make_person, make_union


def lightness(colour: str) -> float:
    red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


class NodeStyleTests(SimpleTestCase):
    def style(self, distance=1, deceased=False, central=False):
        return node_style(
            given_name="Maria Clara",
            surname="Souza Lima",
            distance=distance,
            is_deceased=deceased,
            is_central=central,
        )

    def test_circle_gets_smaller_with_distance(self):
        radii = [self.style(distance=d).radius for d in range(0, 6)]

        self.assertEqual(radii, sorted(radii, reverse=True))
        self.assertGreater(radii[0], radii[-1])

    def test_colour_gets_lighter_with_distance(self):
        near, far = self.style(distance=1).fill, self.style(distance=5).fill

        self.assertGreater(lightness(far), lightness(near))

    def test_person_not_linked_to_the_centre_is_the_smallest(self):
        self.assertEqual(self.style(distance=None).radius, self.style(distance=9).radius)

    def test_living_person_is_a_filled_circle(self):
        style = self.style()

        self.assertNotEqual(style.fill, SURFACE)

    def test_deceased_person_is_only_an_outline(self):
        style = self.style(deceased=True)

        self.assertEqual(style.fill, SURFACE)
        self.assertNotEqual(style.stroke, SURFACE)
        self.assertGreater(style.stroke_width, 0)

    def test_label_is_the_first_name_and_the_last_surname(self):
        self.assertEqual(self.style().label_lines, ["Maria", "Lima"])

    def test_label_of_a_person_without_surname(self):
        style = node_style("Benedita", "", 1, False, False)

        self.assertEqual(style.label_lines, ["Benedita"])

    def test_room_for_a_person_fits_the_circle_and_the_name(self):
        style = node_style("Wilhelmina", "Vasconcellos", 5, False, False)

        self.assertGreater(style.slot_width, 2 * style.radius)
        self.assertGreater(style.slot_width, len("Vasconcellos") * style.font_size * 0.5)


class LineClassTests(SimpleTestCase):
    def test_current_union(self):
        self.assertEqual(union_line_class(kind="marriage", is_ended=False), "current")

    def test_ended_union(self):
        self.assertEqual(union_line_class(kind="marriage", is_ended=True), "ended")

    def test_dating(self):
        self.assertEqual(union_line_class(kind="dating", is_ended=False), "dating")

    def test_union_of_unknown_kind_is_drawn_as_current(self):
        self.assertEqual(union_line_class(kind="", is_ended=False), "current")

    def test_child_lines(self):
        self.assertEqual(child_line_class(BIOLOGICAL), "biological")
        self.assertEqual(child_line_class(ADOPTIVE), "adoptive")
        self.assertEqual(child_line_class(FOSTER), "foster")


class TreePageTests(DemoFamilyTestCase):
    def setUp(self):
        self.html = self.client.get("/pt-br/tree/").content.decode()
        self.svg = re.search(r'<svg id="family-tree".*?</svg>', self.html, re.DOTALL).group(0)

    def test_the_whole_family_is_drawn(self):
        self.assertEqual(self.svg.count('class="person'), Person.objects.count())

    def test_each_person_links_to_their_page(self):
        for identifier in Person.objects.values_list("identifier", flat=True):
            with self.subTest(person=identifier):
                self.assertIn(f'href="/pt-br/people/{identifier}/"', self.svg)

    def test_each_person_shows_their_name(self):
        self.assertIn(">Lia</tspan>", self.svg)
        self.assertIn(">Carvalho</tspan>", self.svg)

    def test_full_name_and_years_appear_when_hovering(self):
        self.assertIn("<title>Anselmo Figueira (1940–2015)</title>", self.svg)

    def test_central_person_has_a_double_ring(self):
        central = re.search(r'<a class="person[^"]*\bcentral\b.*?</a>', self.svg, re.DOTALL).group(0)

        self.assertIn(f"/people/{settings.DEMO_CENTRAL_PERSON}/", central)
        self.assertEqual(central.count("<circle"), 2)
        self.assertEqual(len(re.findall(r'class="person[^"]*\bcentral\b', self.svg)), 1)

    def test_name_of_the_central_person_is_below_the_outer_ring(self):
        central = re.search(r'<a class="person[^"]*\bcentral\b.*?</a>', self.svg, re.DOTALL).group(0)
        ring = re.search(r'<circle class="ring" cx="[\d.-]+" cy="([\d.-]+)" r="([\d.-]+)"', central)
        font_size = float(re.search(r'font-size="([\d.]+)"', central).group(1))
        first_line = float(re.search(r'<tspan x="[\d.-]+" y="([\d.-]+)"', central).group(1))

        ring_bottom = float(ring.group(1)) + float(ring.group(2))
        # The top of the letters (one font size above the baseline) must
        # clear the ring and its 2px stroke.
        self.assertGreaterEqual(first_line - font_size, ring_bottom + 2)

    def test_deceased_people_are_outlines(self):
        deceased = sum(1 for person in Person.objects.all() if person.is_deceased)

        self.assertEqual(len(re.findall(r'class="person[^"]*\bdeceased\b', self.svg)), deceased)

    def test_every_union_is_a_diamond(self):
        self.assertEqual(self.svg.count('class="union-node"'), Union.objects.count())

    def test_union_lines_follow_the_kind_of_union(self):
        ended = Union.objects.filter(ended=True).exclude(kind="dating").count()
        dating = Union.objects.filter(kind="dating").count()
        # Unions with an unknown partner have no line between two people.
        couples = Union.objects.filter(partner2__isnull=False).count()

        self.assertEqual(self.svg.count('class="union-line ended"'), ended)
        self.assertEqual(self.svg.count('class="union-line dating"'), dating)
        self.assertEqual(self.svg.count('class="union-line current"'), couples - ended - dating)

    def test_child_lines_follow_the_kind_of_link(self):
        for kind in ("biological", "adoptive", "foster"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    self.svg.count(f'class="child-line {kind}"'),
                    ChildLink.objects.filter(kind=kind).count(),
                )

    def test_people_with_a_photo_show_it_round_inside_the_circle(self):
        with_photo = Person.objects.exclude(photo="")

        self.assertEqual(self.svg.count('<image class="photo"'), with_photo.count())
        for person in with_photo:
            with self.subTest(person=person.identifier):
                self.assertIn(f'href="/media/v/128/{person.photo.name}.jpg"', self.svg)
        self.assertIn('clip-path="url(#round)"', self.svg)

    def test_everybody_has_the_same_colour(self):
        fills = set(re.findall(r'<circle class="dot"[^>]*fill="([^"]+)"', self.svg))
        allowed = {_mix_with_white(PERSON_COLOR, fade) for fade in FADES} | {SURFACE}

        self.assertTrue(fills)
        self.assertLessEqual(fills, allowed)
        self.assertNotIn("Lado de", self.html)

    def test_deceased_person_with_a_photo_is_marked_for_the_grey_photo(self):
        anselmo = re.search(r'<a class="([^"]*)" href="/pt-br/people/anselmo-figueira-1940/".*?</a>', self.svg, re.DOTALL)

        self.assertIn("deceased", anselmo.group(1))
        self.assertIn('<image class="photo"', anselmo.group(0))

    def test_person_without_a_photo_has_only_the_circle(self):
        davi = re.search(r'href="/pt-br/people/davi-amoreira-1995/".*?</a>', self.svg, re.DOTALL).group(0)

        self.assertNotIn("<image", davi)
        self.assertIn('<circle class="dot"', davi)

    def test_tree_size_copy_of_a_photo_is_served(self):
        response = self.client.get("/media/v/128/people/lia-carvalho-1996.png.jpg")

        self.assertEqual(response.status_code, 200)

    def test_no_see_from_any_more(self):
        self.assertNotIn('id="tree-from"', self.html)
        self.assertNotIn("data/family.js", self.html)

    def test_legend_explains_the_whole_code(self):
        legend = re.search(r'<details class="legend".*?</details>', self.html, re.DOTALL).group(0)

        for text in (
            "Pessoa",
            "Pessoa central",
            "Pessoa falecida",
            "União atual",
            "União terminada",
            "Namoro",
            "Filho biológico",
            "Filho adotivo",
            "Filho de criação",
            "Mais longe",
        ):
            with self.subTest(text=text):
                self.assertIn(text, legend)

    def test_legend_is_translated(self):
        html = self.client.get("/es/tree/").content.decode()

        self.assertIn("Persona fallecida", html)
        self.assertIn("Hijo adoptivo", html)
        self.assertIn('href="/es/people/lia-carvalho-1996/"', html)

    def test_drawing_area_has_the_proportions_of_the_tree(self):
        # So that a narrow screen (a phone) shows no empty space around it.
        left, top, width, height = re.search(r'viewBox="([^"]+)"', self.svg).group(1).split()

        self.assertIn(f'style="aspect-ratio: {width} / {height}"', self.svg)

    def test_page_has_zoom_controls_and_the_script(self):
        self.assertIn('id="tree-zoom-in"', self.html)
        self.assertIn('id="tree-zoom-out"', self.html)
        self.assertIn('id="tree-fit"', self.html)
        self.assertIn("/static/js/tree.js", self.html)

    def test_page_loads_nothing_from_other_servers(self):
        self.assertNotIn('src="http', self.html)
        self.assertNotIn("<link rel=\"stylesheet\" href=\"http", self.html)

    @override_settings(RAIZES_CENTRAL_PERSON="")
    def test_tree_without_a_central_person_is_drawn_with_a_notice(self):
        html = self.client.get("/pt-br/tree/").content.decode()

        self.assertIn("RAIZES_CENTRAL_PERSON", html)
        self.assertEqual(html.count('class="person'), Person.objects.count())
        self.assertNotIn("central\"", html)

    @override_settings(RAIZES_CENTRAL_PERSON="someone-else-1900")
    def test_central_person_that_does_not_exist_gives_a_notice(self):
        html = self.client.get("/pt-br/tree/").content.decode()

        self.assertIn("someone-else-1900", html)
        self.assertIn("RAIZES_CENTRAL_PERSON", html)


class SmallTreeTests(TestCase):
    def test_empty_family_shows_a_notice_instead_of_a_tree(self):
        html = self.client.get("/pt-br/tree/").content.decode()

        self.assertIn("Ninguém foi cadastrado ainda.", html)
        self.assertNotIn("<svg id=\"family-tree\"", html)

    @override_settings(RAIZES_CENTRAL_PERSON="ana-ruiz-1940")
    def test_people_without_any_link_are_drawn_small(self):
        ana = make_person("Ana", "Ruiz", birth_date="1940")
        make_union(ana, make_person("Luis", "Pérez", birth_date="1938"))
        make_person("Solitário", "Silva", birth_date="1950")

        html = self.client.get("/pt-br/tree/").content.decode()
        alone = re.search(r'href="/pt-br/people/solitario-silva-1950/".*?</a>', html, re.DOTALL).group(0)

        self.assertEqual(html.count('class="person'), 3)
        self.assertIn(f'r="{RADII[-1]}"', alone)

"""The skeleton of the tree: where each person and each union is placed.

Positions are calculated from the data. These tests check the rules of the
plan (section 4.2), not exact coordinates.
"""
from itertools import combinations

from django.conf import settings
from django.test import SimpleTestCase

from family.graph import load_family_graph
from family.models import Person
from family.tree_layout import compute_layout

from .test_demo import DemoFamilyTestCase
from .test_kinship import THREE_GENERATIONS, family, union

WIDTH = 80


def layout_of(graph, central, years=None):
    widths = {person: WIDTH for person in graph.people}
    return compute_layout(graph, central, years or {}, widths)


def overlapping_pairs(layout, widths):
    """Pairs of people in the same band whose slots overlap."""
    found = []
    by_layer = {}
    for place in layout.people.values():
        by_layer.setdefault(place.layer, []).append(place)
    for places in by_layer.values():
        for first, second in combinations(places, 2):
            needed = (widths[first.id] + widths[second.id]) / 2
            if abs(first.x - second.x) < needed - 0.01:
                found.append((first.id, second.id))
    return found


class BandsTests(SimpleTestCase):
    def setUp(self):
        self.graph = family(*THREE_GENERATIONS)
        self.layout = layout_of(self.graph, "me")
        self.place = self.layout.people

    def test_everyone_gets_a_position(self):
        self.assertEqual(set(self.place), set(self.graph.people))

    def test_time_runs_from_top_to_bottom(self):
        self.assertLess(self.place["gf1"].y, self.place["father"].y)
        self.assertLess(self.place["father"].y, self.place["me"].y)
        self.assertLess(self.place["me"].y, self.place["child"].y)

    def test_there_is_one_band_per_generation(self):
        self.assertEqual(len(self.layout.bands), 4)
        self.assertEqual(self.place["gf1"].layer, 0)
        self.assertEqual(self.place["child"].layer, 3)

    def test_people_of_the_same_generation_share_a_band(self):
        layers = {self.place[person].layer for person in ("me", "brother", "cousin", "partner")}

        self.assertEqual(len(layers), 1)

    def test_bands_do_not_overlap(self):
        bands = self.layout.bands

        for upper, lower in zip(bands, bands[1:]):
            self.assertLess(upper.bottom, lower.top)

    def test_every_person_is_inside_their_band(self):
        for place in self.place.values():
            band = self.layout.bands[place.layer]
            with self.subTest(person=place.id):
                self.assertGreaterEqual(place.y, band.top)
                self.assertLessEqual(place.y, band.bottom)

    def test_nobody_overlaps(self):
        widths = {person: WIDTH for person in self.graph.people}

        self.assertEqual(overlapping_pairs(self.layout, widths), [])

    def test_layout_is_always_the_same_for_the_same_data(self):
        again = layout_of(family(*THREE_GENERATIONS), "me")

        self.assertEqual(
            {p.id: (p.x, p.y) for p in self.place.values()},
            {p.id: (p.x, p.y) for p in again.people.values()},
        )


class BirthYearTests(SimpleTestCase):
    def test_inside_a_band_older_people_are_higher(self):
        graph = family(union("a b", "old middle young"))
        years = {"old": 1960, "middle": 1970, "young": 1980}

        place = layout_of(graph, "middle", years).people

        self.assertLess(place["old"].y, place["middle"].y)
        self.assertLess(place["middle"].y, place["young"].y)

    def test_people_without_a_known_year_stay_inside_the_band(self):
        graph = family(union("a b", "known unknown"))
        layout = layout_of(graph, "known", {"known": 1960})

        band = layout.bands[layout.people["unknown"].layer]
        self.assertGreaterEqual(layout.people["unknown"].y, band.top)
        self.assertLessEqual(layout.people["unknown"].y, band.bottom)

    def test_uncle_younger_than_the_nephew_is_low_in_his_band_but_above_the_nephew(self):
        graph = family(
            union("gf gm", "father"),
            union("father mother", "me"),
            union("gf later", "young_uncle"),
        )
        years = {"father": 1960, "mother": 1962, "me": 1990, "young_uncle": 1995}

        place = layout_of(graph, "me", years).people

        self.assertEqual(place["young_uncle"].layer, place["father"].layer)
        self.assertGreater(place["young_uncle"].y, place["father"].y)
        self.assertLess(place["young_uncle"].y, place["me"].y)


class UnionPlacementTests(SimpleTestCase):
    def test_each_union_is_a_node_of_its_own(self):
        graph = family(*THREE_GENERATIONS)

        self.assertEqual(len(layout_of(graph, "me").unions), len(graph.unions))

    def test_couple_is_side_by_side_with_the_union_between_them(self):
        layout = layout_of(family(union("a b", "c")), "c")
        place = layout.people
        node = layout.unions[0]

        self.assertAlmostEqual(abs(place["a"].x - place["b"].x), WIDTH + layout.union_gap, delta=0.05)
        self.assertGreater(node.x, min(place["a"].x, place["b"].x))
        self.assertLess(node.x, max(place["a"].x, place["b"].x))
        self.assertTrue(node.is_direct)

    def test_children_are_centred_under_their_union(self):
        layout = layout_of(family(union("a b", "c d e")), "d")
        place = layout.people
        node = layout.unions[0]

        middle = (place["c"].x + place["e"].x) / 2
        self.assertAlmostEqual(node.x, middle, delta=1)

    def test_only_child_is_right_under_the_union(self):
        layout = layout_of(family(union("a b", "c")), "c")

        self.assertAlmostEqual(layout.people["c"].x, layout.unions[0].x, delta=1)

    def test_union_with_an_unknown_partner_sits_beside_the_known_one(self):
        layout = layout_of(family(union("a", "c")), "c")
        node = layout.unions[0]

        self.assertNotEqual(node.x, layout.people["a"].x)
        self.assertLess(abs(node.x - layout.people["a"].x), WIDTH)
        self.assertTrue(node.is_direct)

    def test_person_with_three_unions_has_three_union_nodes_in_date_order(self):
        graph = family(union("hub p1", "c1"), union("hub p2", "c2"), union("hub p3", "c3"))
        layout = layout_of(graph, "c2")
        nodes = sorted(layout.unions, key=lambda node: node.x)

        self.assertEqual([node.record.id for node in nodes], [0, 1, 2])
        self.assertEqual(len({node.x for node in nodes}), 3)

    def test_person_with_three_unions_keeps_two_partners_side_by_side(self):
        graph = family(union("hub p1", "c1"), union("hub p2", "c2"), union("hub p3", "c3"))
        layout = layout_of(graph, "c2")

        self.assertEqual([node.is_direct for node in layout.unions].count(True), 2)

    def test_union_that_jumps_over_someone_is_next_to_the_far_partner(self):
        graph = family(union("hub p1", "c1"), union("hub p2", "c2"), union("hub p3", "c3"))
        layout = layout_of(graph, "c2")
        jumping = next(node for node in layout.unions if not node.is_direct)
        partners = [layout.people[person] for person in jumping.record.partners]
        far = max(partners, key=lambda place: abs(place.x - layout.people["hub"].x))

        self.assertLess(abs(jumping.x - far.x), WIDTH)


class WholeFamilyTests(SimpleTestCase):
    def test_people_not_linked_to_the_central_person_are_still_drawn(self):
        graph = family(union("a b", "me"), union("x y", "z"), extra="alone")
        layout = layout_of(graph, "me")

        self.assertEqual(set(layout.people), set(graph.people))
        self.assertEqual(overlapping_pairs(layout, {p: WIDTH for p in graph.people}), [])
        self.assertLess(layout.people["x"].y, layout.people["z"].y)

    def test_tree_without_a_central_person_is_still_drawn(self):
        graph = family(*THREE_GENERATIONS)
        layout = layout_of(graph, None)

        self.assertEqual(set(layout.people), set(graph.people))
        self.assertLess(layout.people["gf1"].y, layout.people["me"].y)

    def test_central_person_that_does_not_exist_is_treated_as_none(self):
        graph = family(*THREE_GENERATIONS)

        self.assertEqual(set(layout_of(graph, "nobody").people), set(graph.people))

    def test_empty_family(self):
        layout = layout_of(family(), None)

        self.assertEqual(layout.people, {})
        self.assertEqual(layout.unions, [])

    def test_one_person_alone(self):
        layout = layout_of(family(extra="me"), "me")

        self.assertEqual(set(layout.people), {"me"})

    def test_size_of_the_drawing_contains_everyone(self):
        layout = layout_of(family(*THREE_GENERATIONS), "me")

        for place in layout.people.values():
            self.assertGreaterEqual(place.x - WIDTH / 2, layout.left)
            self.assertLessEqual(place.x + WIDTH / 2, layout.right)
            self.assertGreaterEqual(place.y, layout.top)
            self.assertLessEqual(place.y, layout.bottom)

    def test_wide_slots_are_respected(self):
        graph = family(union("a b", "c d e f"))
        widths = {person: WIDTH for person in graph.people}
        widths["d"] = 200
        layout = compute_layout(graph, "c", {}, widths)

        self.assertEqual(overlapping_pairs(layout, widths), [])


class DemoFamilyLayoutTests(DemoFamilyTestCase):
    def setUp(self):
        self.graph = load_family_graph()
        self.years = {person.identifier: person.birth_year for person in Person.objects.all()}
        self.widths = {person: WIDTH for person in self.graph.people}
        self.layout = compute_layout(
            self.graph, settings.DEMO_CENTRAL_PERSON, self.years, self.widths
        )
        self.place = self.layout.people

    def test_the_whole_family_is_in_the_tree(self):
        self.assertEqual(len(self.place), Person.objects.count())
        self.assertEqual(len(self.layout.unions), len(self.graph.unions))

    def test_six_bands_from_the_great_great_grandparents_to_the_children(self):
        self.assertEqual(len(self.layout.bands), 6)
        self.assertEqual(self.place["teodoro-figueira-1885"].layer, 0)
        self.assertEqual(self.place["lia-carvalho-1996"].layer, 4)
        self.assertEqual(self.place["theo-carvalho-2021"].layer, 5)

    def test_nobody_overlaps(self):
        self.assertEqual(overlapping_pairs(self.layout, self.widths), [])

    def test_every_child_is_below_every_parent(self):
        for person in self.graph.people:
            for parent in self.graph.parents(person):
                with self.subTest(child=person, parent=parent.person):
                    self.assertGreater(self.place[person].y, self.place[parent.person].y)

    def test_three_unions_of_the_grandfather(self):
        nodes = [
            node for node in self.layout.unions
            if "joaquim-carvalho-1938" in node.record.partners
        ]

        self.assertEqual(len(nodes), 3)
        self.assertEqual([node.is_direct for node in nodes].count(True), 2)

    def test_eight_siblings_are_in_the_same_band(self):
        siblings = ["helena-figueira-1970"] + self.graph.siblings("helena-figueira-1970").full

        self.assertEqual(len(siblings), 8)
        self.assertEqual(len({self.place[person].layer for person in siblings}), 1)

    def test_siblings_are_side_by_side_in_birth_order(self):
        # Helena is not in this list: she stands beside her partners.
        siblings = [
            "alvaro-figueira-1962",
            "cecilia-figueira-1964",
            "marta-figueira-1966",
            "edgar-figueira-1968",
            "ines-figueira-1972",
            "vitor-figueira-1975",
            "lara-figueira-1978",
        ]
        xs = [self.place[person].x for person in siblings]

        self.assertEqual(xs, sorted(xs))

    def test_partner_from_outside_the_family_is_on_the_same_side_for_every_couple(self):
        couples = [
            ("alvaro-figueira-1962", "rita-palmeira-1965"),
            ("marta-figueira-1966", "paulo-nogueira-1963"),
            ("ines-figueira-1972", "joana-cedro-1974"),
            ("lara-figueira-1978", "mauro-ipe-1976"),
            ("regina-carvalho-1964", "heitor-loureiro-1961"),
        ]

        for relative, partner in couples:
            with self.subTest(couple=relative):
                self.assertLess(self.place[relative].x, self.place[partner].x)

    def test_young_uncle_is_in_the_parents_band_lower_than_his_older_brother(self):
        uncle = self.place["gabriel-carvalho-2000"]
        father = self.place["tomas-carvalho-1968"]
        niece = self.place["lia-carvalho-1996"]

        self.assertEqual(uncle.layer, father.layer)
        self.assertGreater(uncle.y, father.y)
        self.assertLess(uncle.y, niece.y)

    def test_the_three_parental_figures_are_side_by_side(self):
        xs = sorted(
            self.place[person].x
            for person in ("tomas-carvalho-1968", "helena-figueira-1970", "rui-pinheiro-1965")
        )

        self.assertAlmostEqual(xs[1] - xs[0], WIDTH + self.layout.union_gap, delta=0.05)
        self.assertAlmostEqual(xs[2] - xs[1], WIDTH + self.layout.union_gap, delta=0.05)
        self.assertEqual(self.place["helena-figueira-1970"].x, xs[1])

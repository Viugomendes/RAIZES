"""The kinship rules: everything the site calculates instead of asking for.

Most tests build a tiny family in memory (no database). Letters stand for
people: `union("a b", "c d")` is a couple a+b with the children c and d.
"""
from django.conf import settings
from django.test import SimpleTestCase

from family.graph import load_family_graph
from family.kinship import (
    ADOPTIVE,
    BIOLOGICAL,
    CENTER,
    FOSTER,
    FamilyGraph,
    UnionRecord,
)
from family.models import Person

from .test_demo import DemoFamilyTestCase


def union(partners, children="", adoptive="", foster=""):
    links = [(child, BIOLOGICAL) for child in children.split()]
    links += [(child, ADOPTIVE) for child in adoptive.split()]
    links += [(child, FOSTER) for child in foster.split()]
    return (tuple(partners.split()), tuple(links))


def family(*unions, extra=""):
    """Build a graph; people are listed in the order they first appear."""
    people = []
    records = []
    for number, (partners, links) in enumerate(unions):
        for person in list(partners) + [child for child, _kind in links]:
            if person not in people:
                people.append(person)
        records.append(UnionRecord(number, partners, links))
    people += [person for person in extra.split() if person not in people]
    return FamilyGraph(people, records)


def ids(relatives):
    return [relative.person for relative in relatives]


# A family with three generations and both sides, used by several tests:
#
#   gf1 + gm1            gf2 + gm2
#     |                    |
#   uncle, father  +  mother, aunt + aunt_husband
#                  |                |
#        brother, me + partner     cousin
#                  |
#                child
THREE_GENERATIONS = (
    union("gf1 gm1", "uncle father"),
    union("gf2 gm2", "mother aunt"),
    union("father mother", "brother me"),
    union("aunt aunt_husband", "cousin"),
    union("me partner", "child"),
)


class ParentsTests(SimpleTestCase):
    def test_child_of_a_couple_has_two_biological_parents(self):
        graph = family(union("a b", "c"))

        self.assertEqual(
            [(p.person, p.kind) for p in graph.parents("c")],
            [("a", BIOLOGICAL), ("b", BIOLOGICAL)],
        )

    def test_child_of_a_union_with_an_unknown_partner_has_one_parent(self):
        graph = family(union("a", "c"))

        self.assertEqual(ids(graph.parents("c")), ["a"])

    def test_person_who_is_not_a_child_of_any_union_has_no_parents(self):
        graph = family(union("a b", "c"))

        self.assertEqual(graph.parents("a"), [])

    def test_adopted_child_has_adoptive_parents(self):
        graph = family(union("a b", adoptive="c"))

        self.assertEqual({p.kind for p in graph.parents("c")}, {ADOPTIVE})

    def test_three_parental_figures(self):
        graph = family(
            union("mother father", "me"),
            union("mother stepfather", foster="me"),
        )

        self.assertEqual(
            [(p.person, p.kind) for p in graph.parents("me")],
            [("mother", BIOLOGICAL), ("father", BIOLOGICAL), ("stepfather", FOSTER)],
        )

    def test_parent_reached_by_two_links_keeps_the_strongest_one(self):
        graph = family(
            union("mother stepfather", foster="me"),
            union("mother father", "me"),
        )

        kinds = {p.person: p.kind for p in graph.parents("me")}

        self.assertEqual(kinds["mother"], BIOLOGICAL)

    def test_biological_parents_come_before_adoptive_and_foster_ones(self):
        graph = family(
            union("raised_me", foster="me"),
            union("adopted_me", adoptive="me"),
            union("mother", "me"),
        )

        self.assertEqual(ids(graph.parents("me")), ["mother", "adopted_me", "raised_me"])


class ChildrenTests(SimpleTestCase):
    def test_children_of_every_union_of_a_person(self):
        graph = family(union("a b", "c d"), union("a x", "e"))

        self.assertEqual(ids(graph.children("a")), ["c", "d", "e"])
        self.assertEqual(ids(graph.children("b")), ["c", "d"])

    def test_child_keeps_the_kind_of_link(self):
        graph = family(union("a b", "c", adoptive="d", foster="e"))

        self.assertEqual(
            {c.person: c.kind for c in graph.children("a")},
            {"c": BIOLOGICAL, "d": ADOPTIVE, "e": FOSTER},
        )

    def test_child_linked_through_two_unions_is_listed_once(self):
        graph = family(union("mother father", "me"), union("mother stepfather", foster="me"))

        self.assertEqual(
            [(c.person, c.kind) for c in graph.children("mother")], [("me", BIOLOGICAL)]
        )

    def test_person_without_children(self):
        graph = family(union("a b", "c"))

        self.assertEqual(graph.children("c"), [])

    def test_grandchildren(self):
        graph = family(union("a b", "c d"), union("c x", "e f"), union("d y", "g"))

        self.assertEqual(graph.grandchildren("a"), ["e", "f", "g"])

    def test_grandchild_reached_through_two_children_is_listed_once(self):
        graph = family(union("a b", "c"), union("a x", "d"), union("c d", "e"))

        self.assertEqual(graph.grandchildren("a"), ["e"])

    def test_person_without_grandchildren(self):
        graph = family(union("a b", "c"))

        self.assertEqual(graph.grandchildren("a"), [])


class SiblingsTests(SimpleTestCase):
    def test_children_of_the_same_union_are_full_siblings(self):
        graph = family(union("a b", "c d e"))

        siblings = graph.siblings("d")

        self.assertEqual(siblings.full, ["c", "e"])
        self.assertEqual(siblings.half, [])
        self.assertEqual(siblings.step, [])

    def test_only_child_has_no_siblings(self):
        graph = family(union("a b", "c"))

        self.assertEqual(graph.siblings("c").all, [])

    def test_children_who_share_one_parent_are_half_siblings(self):
        graph = family(union("a b", "c"), union("a x", "d"))

        self.assertEqual(graph.siblings("c").half, ["d"])
        self.assertEqual(graph.siblings("c").full, [])

    def test_children_of_the_same_union_with_an_unknown_partner_are_full_siblings(self):
        graph = family(union("a", "c d"))

        self.assertEqual(graph.siblings("c").full, ["d"])

    def test_adopted_and_biological_children_of_a_couple_are_full_siblings(self):
        graph = family(union("a b", "c", adoptive="d"))

        self.assertEqual(graph.siblings("c").full, ["d"])
        self.assertEqual(graph.siblings("d").full, ["c"])

    def test_child_of_mother_and_stepfather_is_a_half_sibling(self):
        graph = family(
            union("mother father", "me"),
            union("mother stepfather", "nina", foster="me"),
        )

        self.assertEqual(graph.siblings("me").half, ["nina"])
        self.assertEqual(graph.siblings("me").full, [])
        self.assertEqual(graph.siblings("nina").half, ["me"])

    def test_child_of_the_stepfather_alone_is_a_step_sibling(self):
        graph = family(
            union("mother father", "me"),
            union("mother stepfather", foster="me"),
            union("stepfather ex", "otavio"),
        )

        self.assertEqual(graph.siblings("me").step, ["otavio"])
        self.assertEqual(graph.siblings("me").half, [])
        self.assertEqual(graph.siblings("otavio").step, ["me"])

    def test_each_sibling_is_in_only_one_group(self):
        graph = family(
            union("mother father", "me brother"),
            union("mother stepfather", foster="me brother"),
        )

        siblings = graph.siblings("me")

        self.assertEqual(siblings.full, ["brother"])
        self.assertEqual(siblings.half + siblings.step, [])

    def test_all_siblings_lists_full_then_half_then_step(self):
        graph = family(
            union("mother father", "me brother"),
            union("mother stepfather", "nina", foster="me brother"),
            union("stepfather ex", "otavio"),
        )

        self.assertEqual(graph.siblings("me").all, ["brother", "nina", "otavio"])


class PartnersTests(SimpleTestCase):
    def test_partners_in_the_order_of_the_unions(self):
        graph = family(union("a b"), union("a c"), union("d a"))

        self.assertEqual(graph.partners("a"), ["b", "c", "d"])

    def test_unknown_partner_is_not_listed(self):
        graph = family(union("a", "c"))

        self.assertEqual(graph.partners("a"), [])

    def test_unions_of_a_person(self):
        graph = family(union("a b"), union("c d"), union("a c"))

        self.assertEqual([record.id for record in graph.unions_of("a")], [0, 2])


class DistanceTests(SimpleTestCase):
    def setUp(self):
        self.distance = family(*THREE_GENERATIONS, extra="stranger").distances("me")

    def test_central_person_is_at_distance_zero(self):
        self.assertEqual(self.distance["me"], 0)

    def test_parents_partner_and_children_are_one_step_away(self):
        for person in ("father", "mother", "partner", "child"):
            with self.subTest(person=person):
                self.assertEqual(self.distance[person], 1)

    def test_siblings_and_grandparents_are_two_steps_away(self):
        for person in ("brother", "gf1", "gm1", "gf2", "gm2"):
            with self.subTest(person=person):
                self.assertEqual(self.distance[person], 2)

    def test_uncles_are_three_steps_away(self):
        self.assertEqual(self.distance["uncle"], 3)
        self.assertEqual(self.distance["aunt"], 3)

    def test_cousins_and_relatives_by_marriage_are_further(self):
        self.assertEqual(self.distance["cousin"], 4)
        self.assertEqual(self.distance["aunt_husband"], 4)

    def test_person_not_linked_to_the_central_person_has_no_distance(self):
        self.assertNotIn("stranger", self.distance)


class GenerationTests(SimpleTestCase):
    def setUp(self):
        self.generation = family(*THREE_GENERATIONS, extra="stranger").generations("me")

    def test_central_person_is_generation_zero(self):
        self.assertEqual(self.generation["me"], 0)

    def test_siblings_cousins_and_partner_share_the_generation(self):
        for person in ("brother", "cousin", "partner"):
            with self.subTest(person=person):
                self.assertEqual(self.generation[person], 0)

    def test_parents_and_uncles_are_one_generation_above(self):
        for person in ("father", "mother", "uncle", "aunt", "aunt_husband"):
            with self.subTest(person=person):
                self.assertEqual(self.generation[person], -1)

    def test_grandparents_are_two_generations_above(self):
        for person in ("gf1", "gm1", "gf2", "gm2"):
            with self.subTest(person=person):
                self.assertEqual(self.generation[person], -2)

    def test_children_are_one_generation_below(self):
        self.assertEqual(self.generation["child"], 1)

    def test_person_not_linked_to_the_central_person_has_no_generation(self):
        self.assertNotIn("stranger", self.generation)

    def test_generation_follows_the_family_not_the_age(self):
        # "late" is the grandfather's child with a later partner: an uncle of
        # "me", in the parents' generation, however young he is.
        graph = family(
            union("gf gm", "father"),
            union("father mother", "me"),
            union("gf later_partner", "late"),
        )

        self.assertEqual(graph.generations("me")["late"], -1)
        self.assertEqual(graph.generations("me")["later_partner"], -2)


class SideTests(SimpleTestCase):
    def setUp(self):
        self.graph = family(*THREE_GENERATIONS, extra="stranger")
        self.side = self.graph.sides("me")

    def test_parental_figures_of_the_central_person(self):
        self.assertEqual(self.graph.parental_figures("me"), ["father", "mother"])

    def test_each_parent_is_on_their_own_side(self):
        self.assertEqual(self.side["father"], "father")
        self.assertEqual(self.side["mother"], "mother")

    def test_relatives_reached_through_the_father_are_on_his_side(self):
        for person in ("gf1", "gm1", "uncle"):
            with self.subTest(person=person):
                self.assertEqual(self.side[person], "father")

    def test_relatives_reached_through_the_mother_are_on_her_side(self):
        for person in ("gf2", "gm2", "aunt", "aunt_husband", "cousin"):
            with self.subTest(person=person):
                self.assertEqual(self.side[person], "mother")

    def test_central_person_and_full_siblings_belong_to_no_single_side(self):
        self.assertEqual(self.side["me"], CENTER)
        self.assertEqual(self.side["brother"], CENTER)

    def test_partner_and_children_of_the_central_person_belong_to_no_side(self):
        self.assertEqual(self.side["partner"], CENTER)
        self.assertEqual(self.side["child"], CENTER)

    def test_person_not_linked_to_the_central_person_has_no_side(self):
        self.assertNotIn("stranger", self.side)

    def test_three_parental_figures_make_three_sides(self):
        graph = family(
            union("mother father", "me"),
            union("mother stepfather", "nina", foster="me"),
            union("step_grandmother", "stepfather"),
            union("stepfather ex", "otavio"),
        )
        side = graph.sides("me")

        self.assertEqual(graph.parental_figures("me"), ["mother", "father", "stepfather"])
        self.assertEqual(side["step_grandmother"], "stepfather")
        self.assertEqual(side["otavio"], "stepfather")
        self.assertEqual(side["ex"], "stepfather")
        self.assertEqual(side["nina"], CENTER)  # reached through mother and stepfather alike

    def test_person_linked_through_two_sides_stays_on_the_shortest_path(self):
        # The father's brother married the mother's cousin. She is 4 steps
        # away through the father and 5 through the mother, so she is shown
        # on the father's side, although she is the mother's blood relative.
        graph = family(
            union("pgf pgm", "father uncle"),
            union("mggf mggm", "mgf great_uncle"),
            union("mgf mgm", "mother"),
            union("great_uncle x", "mothers_cousin"),
            union("father mother", "me"),
            union("uncle mothers_cousin"),
        )
        side = graph.sides("me")

        self.assertEqual(graph.distances("me")["mothers_cousin"], 4)
        self.assertEqual(side["mothers_cousin"], "father")
        self.assertEqual(side["great_uncle"], "mother")

    def test_central_person_without_parents_has_no_sides(self):
        graph = family(union("me partner", "child"))

        self.assertEqual(graph.parental_figures("me"), [])
        self.assertEqual(set(graph.sides("me").values()), {CENTER})


class DemoFamilyKinshipTests(DemoFamilyTestCase):
    """The same rules, checked against the invented family in the database."""

    def setUp(self):
        self.graph = load_family_graph()
        self.central = settings.DEMO_CENTRAL_PERSON

    def test_everyone_in_the_demo_family_is_in_the_graph(self):
        self.assertEqual(len(self.graph.people), Person.objects.count())

    def test_central_person_has_three_parental_figures(self):
        self.assertEqual(
            [(p.person, p.kind) for p in self.graph.parents(self.central)],
            [
                ("tomas-carvalho-1968", BIOLOGICAL),
                ("helena-figueira-1970", BIOLOGICAL),
                ("rui-pinheiro-1965", FOSTER),
            ],
        )

    def test_central_person_has_full_half_and_step_siblings(self):
        siblings = self.graph.siblings(self.central)

        self.assertEqual(siblings.full, ["bento-carvalho-1993"])
        self.assertEqual(siblings.half, ["nina-pinheiro-2007"])
        self.assertEqual(siblings.step, ["otavio-pinheiro-1990"])

    def test_mother_has_seven_siblings_in_birth_order(self):
        self.assertEqual(
            self.graph.siblings("helena-figueira-1970").full,
            [
                "alvaro-figueira-1962",
                "cecilia-figueira-1964",
                "marta-figueira-1966",
                "edgar-figueira-1968",
                "ines-figueira-1972",
                "vitor-figueira-1975",
                "lara-figueira-1978",
            ],
        )

    def test_father_has_a_full_sister_and_two_half_brothers(self):
        siblings = self.graph.siblings("tomas-carvalho-1968")

        self.assertEqual(siblings.full, ["regina-carvalho-1964"])
        self.assertEqual(siblings.half, ["marcos-carvalho-1984", "gabriel-carvalho-2000"])

    def test_grandfather_with_three_unions(self):
        self.assertEqual(
            self.graph.partners("joaquim-carvalho-1938"),
            ["amelia-castanheira-1941", "lucia-laranjeira-1950", "sonia-cerejeira-1966"],
        )
        self.assertEqual(
            ids(self.graph.children("joaquim-carvalho-1938")),
            [
                "regina-carvalho-1964",
                "tomas-carvalho-1968",
                "marcos-carvalho-1984",
                "gabriel-carvalho-2000",
            ],
        )
        self.assertEqual(
            self.graph.grandchildren("joaquim-carvalho-1938"),
            [
                "rafael-loureiro-1988",
                "beatriz-loureiro-1991",
                "bento-carvalho-1993",
                "lia-carvalho-1996",
            ],
        )

    def test_adopted_cousin_is_a_child_and_a_full_sibling(self):
        marta_children = {c.person: c.kind for c in self.graph.children("marta-figueira-1966")}

        self.assertEqual(marta_children["jonas-nogueira-2001"], ADOPTIVE)
        self.assertEqual(self.graph.siblings("jonas-nogueira-2001").full, ["clara-nogueira-1995"])

    def test_person_with_an_unknown_father_has_one_parent(self):
        self.assertEqual(ids(self.graph.parents("rui-pinheiro-1965")), ["zelia-pinheiro-1942"])

    def test_generations_go_from_four_above_to_one_below(self):
        generation = self.graph.generations(self.central)

        self.assertEqual(min(generation.values()), -4)
        self.assertEqual(max(generation.values()), 1)
        self.assertEqual(generation["teodoro-figueira-1885"], -4)
        self.assertEqual(generation["baltazar-carvalho-1880"], -4)
        self.assertEqual(generation["theo-carvalho-2021"], 1)

    def test_uncle_younger_than_his_niece_is_still_in_the_parents_generation(self):
        generation = self.graph.generations(self.central)
        uncle = Person.objects.get(identifier="gabriel-carvalho-2000")
        niece = Person.objects.get(identifier=self.central)

        self.assertGreater(uncle.birth_year, niece.birth_year)
        self.assertEqual(generation[uncle.identifier], -1)

    def test_sides_of_the_demo_family(self):
        side = self.graph.sides(self.central)

        self.assertEqual(side["anselmo-figueira-1940"], "helena-figueira-1970")
        self.assertEqual(side["jonas-nogueira-2001"], "helena-figueira-1970")
        self.assertEqual(side["joaquim-carvalho-1938"], "tomas-carvalho-1968")
        self.assertEqual(side["gabriel-carvalho-2000"], "tomas-carvalho-1968")
        self.assertEqual(side["zelia-pinheiro-1942"], "rui-pinheiro-1965")
        self.assertEqual(side["otavio-pinheiro-1990"], "rui-pinheiro-1965")
        for person in ("bento-carvalho-1993", "nina-pinheiro-2007", "davi-amoreira-1995", "theo-carvalho-2021"):
            with self.subTest(person=person):
                self.assertEqual(side[person], CENTER)

    def test_distances_of_the_demo_family(self):
        distance = self.graph.distances(self.central)

        self.assertEqual(distance["helena-figueira-1970"], 1)
        self.assertEqual(distance["davi-amoreira-1995"], 1)
        self.assertEqual(distance["bento-carvalho-1993"], 2)
        self.assertEqual(distance["gabriel-carvalho-2000"], 3)
        self.assertEqual(distance["jonas-nogueira-2001"], 4)
        self.assertEqual(distance["teodoro-figueira-1885"], 4)

    def test_everyone_in_the_demo_family_is_linked_to_the_central_person(self):
        self.assertEqual(len(self.graph.distances(self.central)), Person.objects.count())

"""How the period of a union is written: "1992–2003", "desde 2005"..."""
from django.test import TestCase

from family.person_page import union_period

from .test_models import make_person, make_union


class UnionPeriodTests(TestCase):
    def setUp(self):
        self.ana = make_person("Ana", "Ruiz", birth_date="1940")
        self.luis = make_person("Luis", "Pérez", birth_date="1938")

    def period(self, **fields):
        return union_period(make_union(self.ana, self.luis, **fields))

    def test_start_and_end(self):
        self.assertEqual(self.period(start_date="1992-05-01", end_date="2003"), "1992–2003")

    def test_current_union_with_a_known_start(self):
        self.assertEqual(self.period(start_date="2005"), "desde 2005")

    def test_ended_union_with_an_unknown_end(self):
        self.assertEqual(self.period(start_date="1992", ended=True), "1992–?")

    def test_only_the_end_is_known(self):
        self.assertEqual(self.period(end_date="2003"), "até 2003")

    def test_nothing_is_known(self):
        self.assertEqual(self.period(), "")

    def test_union_lasts_until_the_first_death(self):
        self.luis.death_date = "1979-05-30"
        self.luis.save()
        self.ana.death_date = "2001"
        self.ana.save()

        self.assertEqual(self.period(start_date="1962"), "1962–1979")

    def test_separation_before_the_death_keeps_the_separation_year(self):
        self.luis.death_date = "1999"
        self.luis.save()

        self.assertEqual(self.period(start_date="1962", end_date="1980"), "1962–1980")

    def test_partner_who_died_on_an_unknown_date(self):
        self.luis.deceased = True
        self.luis.save()

        self.assertEqual(self.period(start_date="1962"), "1962–?")

    def test_death_without_a_known_start(self):
        self.luis.death_date = "1979"
        self.luis.save()

        self.assertEqual(self.period(), "até 1979")

    def test_union_with_an_unknown_partner(self):
        union = make_union(self.ana, start_date="1960")

        self.assertEqual(union_period(union), "desde 1960")

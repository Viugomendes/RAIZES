"""Dates that may be complete or only a year."""
from django.test import SimpleTestCase
from django.utils import translation

from family.dates import PartialDate


class PartialDateParsingTests(SimpleTestCase):
    def test_only_the_year(self):
        date = PartialDate.parse("1962")

        self.assertEqual((date.year, date.month, date.day), (1962, None, None))

    def test_complete_date_in_iso_format(self):
        date = PartialDate.parse("1962-03-14")

        self.assertEqual((date.year, date.month, date.day), (1962, 3, 14))

    def test_complete_date_in_brazilian_format(self):
        self.assertEqual(PartialDate.parse("14/03/1962"), PartialDate(1962, 3, 14))

    def test_single_digit_day_and_month(self):
        self.assertEqual(PartialDate.parse("4/3/1962"), PartialDate(1962, 3, 4))

    def test_surrounding_spaces_are_ignored(self):
        self.assertEqual(PartialDate.parse("  1962 "), PartialDate(1962))

    def test_empty_text_means_unknown(self):
        self.assertIsNone(PartialDate.parse(""))
        self.assertIsNone(PartialDate.parse(None))

    def test_impossible_day_is_rejected(self):
        with self.assertRaises(ValueError):
            PartialDate.parse("1962-02-30")

    def test_text_that_is_not_a_date_is_rejected(self):
        for text in ("abc", "62", "1962-03", "14-03-1962", "1962/03/14", "0999"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                PartialDate.parse(text)


class PartialDateBehaviourTests(SimpleTestCase):
    def test_is_stored_as_iso_text(self):
        self.assertEqual(str(PartialDate(1962)), "1962")
        self.assertEqual(str(PartialDate(1962, 3, 4)), "1962-03-04")

    def test_year_only_sorts_before_a_complete_date_of_the_same_year(self):
        dates = [PartialDate(1962, 3, 14), PartialDate(1962), PartialDate(1950, 12, 1)]

        self.assertEqual(
            sorted(dates),
            [PartialDate(1950, 12, 1), PartialDate(1962), PartialDate(1962, 3, 14)],
        )

    def test_complete_dates_are_compared_by_day(self):
        self.assertTrue(PartialDate(1962, 3, 13).is_surely_before(PartialDate(1962, 3, 14)))
        self.assertFalse(PartialDate(1962, 3, 14).is_surely_before(PartialDate(1962, 3, 14)))

    def test_year_only_dates_are_compared_by_year(self):
        self.assertTrue(PartialDate(1961).is_surely_before(PartialDate(1962, 3, 14)))
        self.assertFalse(PartialDate(1962).is_surely_before(PartialDate(1962, 3, 14)))
        self.assertFalse(PartialDate(1962, 3, 14).is_surely_before(PartialDate(1962)))

    def test_year_only_is_shown_as_the_year(self):
        self.assertEqual(PartialDate(1962).display(), "1962")

    def test_approximate_date_shows_only_the_year_with_c(self):
        self.assertEqual(PartialDate(1962, 3, 14).display(approximate=True), "c. 1962")

    def test_complete_date_is_written_out_in_portuguese(self):
        with translation.override("pt-br"):
            self.assertEqual(PartialDate(1962, 3, 14).display(), "14 de março de 1962")

    def test_complete_date_is_written_out_in_spanish(self):
        with translation.override("es"):
            self.assertEqual(PartialDate(1962, 3, 14).display(), "14 de marzo de 1962")

"""The stable identifier of a person: name-surname-year."""
from django.test import SimpleTestCase

from family.identifiers import is_valid_identifier, suggest_identifier


def nothing_taken(identifier):
    return False


class SuggestIdentifierTests(SimpleTestCase):
    def test_first_name_first_surname_and_year(self):
        self.assertEqual(
            suggest_identifier("Ramón", "García Ortega", 1962, nothing_taken),
            "ramon-garcia-1962",
        )

    def test_accents_and_cedilla_are_removed(self):
        self.assertEqual(
            suggest_identifier("Conceição", "Araújo", 1950, nothing_taken),
            "conceicao-araujo-1950",
        )

    def test_only_the_first_given_name_is_used(self):
        self.assertEqual(
            suggest_identifier("Maria Clara", "Silva", 1990, nothing_taken),
            "maria-silva-1990",
        )

    def test_particles_of_the_surname_are_skipped(self):
        self.assertEqual(
            suggest_identifier("João", "da Silva", 1930, nothing_taken),
            "joao-silva-1930",
        )

    def test_unknown_year_uses_a_number(self):
        self.assertEqual(
            suggest_identifier("Maria", "Silva", None, nothing_taken), "maria-silva-1"
        )

    def test_unknown_year_takes_the_next_free_number(self):
        taken = {"maria-silva-1", "maria-silva-2"}

        self.assertEqual(
            suggest_identifier("Maria", "Silva", None, taken.__contains__),
            "maria-silva-3",
        )

    def test_same_name_and_year_gets_a_suffix(self):
        taken = {"ramon-garcia-1962"}

        self.assertEqual(
            suggest_identifier("Ramón", "García", 1962, taken.__contains__),
            "ramon-garcia-1962-2",
        )

    def test_person_without_surname(self):
        self.assertEqual(
            suggest_identifier("Benedita", "", 1890, nothing_taken), "benedita-1890"
        )


class IdentifierFormatTests(SimpleTestCase):
    def test_valid_identifiers(self):
        for identifier in ("ramon-garcia-1962", "maria-silva-2", "benedita-1890"):
            with self.subTest(identifier=identifier):
                self.assertTrue(is_valid_identifier(identifier))

    def test_invalid_identifiers(self):
        for identifier in ("Ramon-Garcia", "ramón-garcia", "ramon garcia", "-ramon", "ramon--garcia", ""):
            with self.subTest(identifier=identifier):
                self.assertFalse(is_valid_identifier(identifier))

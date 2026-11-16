"""The data models and their validations."""
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.utils import translation

from family.models import ChildLink, Person, Place, Union


def make_person(given_name="Ramón", surname="García Ortega", **fields) -> Person:
    """Create a person the way the admin does: validate, then save."""
    person = Person(given_name=given_name, surname=surname, **fields)
    person.full_clean()
    person.save()
    return person


def make_union(partner1, partner2=None, children=(), **fields) -> Union:
    union = Union(partner1=partner1, partner2=partner2, **fields)
    union.full_clean()
    union.save()
    for child in children:
        link = ChildLink(union=union, child=child)
        link.full_clean()
        link.save()
    return union


class PersonIdentifierTests(TestCase):
    def test_identifier_is_created_from_name_and_birth_year(self):
        person = make_person(birth_date="1962-03-14")

        self.assertEqual(person.identifier, "ramon-garcia-1962")

    def test_second_person_with_same_name_and_year_gets_a_suffix(self):
        make_person(birth_date="1962")
        second = make_person(birth_date="1962")

        self.assertEqual(second.identifier, "ramon-garcia-1962-2")

    def test_unknown_birth_year_uses_a_number(self):
        self.assertEqual(make_person("Maria", "Silva").identifier, "maria-silva-1")

    def test_typed_identifier_is_kept(self):
        person = make_person(identifier="el-moncho-1962", birth_date="1962")

        self.assertEqual(person.identifier, "el-moncho-1962")

    def test_identifier_with_invalid_characters_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            make_person(identifier="Ramón García")

        self.assertIn("identifier", caught.exception.message_dict)

    def test_repeated_identifier_is_rejected(self):
        make_person(identifier="ramon-garcia-1962")

        with self.assertRaises(ValidationError) as caught:
            make_person(identifier="ramon-garcia-1962")

        self.assertIn("identifier", caught.exception.message_dict)

    def test_identifier_does_not_change_when_name_or_date_is_corrected(self):
        person = make_person(birth_date="1962")
        person.given_name = "Raimundo"
        person.birth_date = "1963"
        person.full_clean()
        person.save()

        self.assertEqual(Person.objects.get(pk=person.pk).identifier, "ramon-garcia-1962")

    def test_changing_the_identifier_is_rejected(self):
        person = make_person(birth_date="1962")
        person.identifier = "another-name-1962"

        with self.assertRaises(ValidationError) as caught:
            person.full_clean()

        self.assertIn("identifier", caught.exception.message_dict)

    def test_saving_a_changed_identifier_without_validating_is_refused(self):
        person = make_person(birth_date="1962")
        person.identifier = "another-name-1962"

        with self.assertRaises(ValueError):
            person.save()


class PersonDateTests(TestCase):
    def test_brazilian_date_format_is_stored_as_iso(self):
        person = make_person(birth_date="14/03/1962")

        self.assertEqual(person.birth_date, "1962-03-14")

    def test_invalid_date_has_a_message_in_portuguese(self):
        with translation.override("pt-br"), self.assertRaises(ValidationError) as caught:
            make_person(birth_date="31/02/1962")

        self.assertEqual(
            caught.exception.message_dict["birth_date"],
            ["Escreva a data como DD/MM/AAAA ou só o ano (AAAA)."],
        )

    def test_death_before_birth_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            make_person(birth_date="1962", death_date="1950")

        self.assertIn("death_date", caught.exception.message_dict)

    def test_death_in_the_birth_year_is_accepted_when_only_the_year_is_known(self):
        person = make_person(birth_date="1962-03-14", death_date="1962")

        self.assertEqual(person.death_date, "1962")

    def test_person_with_death_date_is_marked_as_deceased(self):
        person = make_person(birth_date="1900", death_date="1980")

        self.assertTrue(person.deceased)
        self.assertTrue(person.is_deceased)

    def test_person_can_be_deceased_without_a_known_date(self):
        person = make_person(deceased=True)

        self.assertTrue(person.is_deceased)

    def test_years_of_a_living_person(self):
        self.assertEqual(make_person(birth_date="1962-03-14").years_display, "1962")

    def test_years_of_a_deceased_person(self):
        person = make_person(birth_date="1900-01-02", death_date="1980")

        self.assertEqual(person.years_display, "1900–1980")

    def test_years_with_an_approximate_birth(self):
        person = make_person(
            birth_date="1885", birth_date_approximate=True, death_date="1950"
        )

        self.assertEqual(person.years_display, "c. 1885–1950")

    def test_years_of_a_deceased_person_without_death_date(self):
        self.assertEqual(make_person(birth_date="1885", deceased=True).years_display, "1885–?")

    def test_years_when_only_the_death_is_known(self):
        self.assertEqual(make_person(death_date="1950").years_display, "?–1950")

    def test_years_when_nothing_is_known(self):
        self.assertEqual(make_person().years_display, "")


class PersonFieldTests(TestCase):
    def test_full_name(self):
        self.assertEqual(make_person().full_name, "Ramón García Ortega")

    def test_full_name_without_surname(self):
        self.assertEqual(make_person("Benedita", "").full_name, "Benedita")

    def test_tags_are_tidied_up(self):
        person = make_person(tags="  Músico, emigrante ,músico,, ")

        self.assertEqual(person.tags, "músico, emigrante")
        self.assertEqual(person.tag_list, ["músico", "emigrante"])

    def test_interview_accepts_the_two_youtube_formats(self):
        first = make_person(interview_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        second = make_person(interview_url="https://youtu.be/dQw4w9WgXcQ")

        self.assertEqual(first.youtube_id, "dQw4w9WgXcQ")
        self.assertEqual(second.youtube_id, "dQw4w9WgXcQ")

    def test_interview_from_another_site_has_a_message_in_portuguese(self):
        with translation.override("pt-br"), self.assertRaises(ValidationError) as caught:
            make_person(interview_url="https://vimeo.com/123456")

        self.assertEqual(
            caught.exception.message_dict["interview_url"],
            [
                "Cole o link do vídeo no YouTube, num destes formatos: "
                "https://www.youtube.com/watch?v=CODIGO ou https://youtu.be/CODIGO."
            ],
        )

    def test_person_without_interview_has_no_video(self):
        self.assertIsNone(make_person().youtube_id)

    def test_place_in_use_cannot_be_deleted(self):
        place = Place.objects.create(slug="valencia", name="Valência, Espanha")
        make_person(birth_place=place)

        with self.assertRaises(ProtectedError):
            place.delete()


class PlaceTests(TestCase):
    def test_latitude_out_of_range_is_rejected(self):
        place = Place(slug="nowhere", name="Nowhere", latitude=120, longitude=10)

        with self.assertRaises(ValidationError) as caught:
            place.full_clean()

        self.assertIn("latitude", caught.exception.message_dict)

    def test_latitude_without_longitude_is_rejected(self):
        place = Place(slug="half", name="Half", latitude=10)

        with self.assertRaises(ValidationError) as caught:
            place.full_clean()

        self.assertIn("longitude", caught.exception.message_dict)

    def test_place_without_coordinates_is_accepted(self):
        Place(slug="somewhere", name="Somewhere").full_clean()


class UnionTests(TestCase):
    def setUp(self):
        self.ramon = make_person(birth_date="1962")
        self.carmen = make_person("Carmen", "López", birth_date="1964")

    def test_union_between_two_people(self):
        union = make_union(self.ramon, self.carmen, kind=Union.Kind.MARRIAGE, start_date="1988")

        self.assertEqual(union.partners, [self.ramon, self.carmen])
        self.assertEqual(union.partner_of(self.ramon), self.carmen)

    def test_union_with_an_unknown_partner(self):
        union = make_union(self.carmen)

        self.assertEqual(union.partners, [self.carmen])
        self.assertIsNone(union.partner_of(self.carmen))

    def test_person_cannot_be_in_a_union_with_themselves(self):
        with self.assertRaises(ValidationError) as caught:
            make_union(self.ramon, self.ramon)

        self.assertIn("partner2", caught.exception.message_dict)

    def test_end_before_start_is_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            make_union(self.ramon, self.carmen, start_date="1988", end_date="1980")

        self.assertIn("end_date", caught.exception.message_dict)

    def test_union_without_end_is_current(self):
        self.assertFalse(make_union(self.ramon, self.carmen, start_date="1988").is_ended)

    def test_union_with_end_date_is_ended(self):
        union = make_union(self.ramon, self.carmen, start_date="1988", end_date="2001")

        self.assertTrue(union.is_ended)
        self.assertTrue(union.ended)

    def test_union_can_be_ended_without_a_known_date(self):
        self.assertTrue(make_union(self.ramon, self.carmen, ended=True).is_ended)

    def test_person_in_a_union_cannot_be_deleted(self):
        make_union(self.ramon, self.carmen)

        with self.assertRaises(ProtectedError):
            self.ramon.delete()


class ChildLinkTests(TestCase):
    def setUp(self):
        self.ramon = make_person(birth_date="1962")
        self.carmen = make_person("Carmen", "López", birth_date="1964")
        self.javier = make_person("Javier", "García", birth_date="1990")
        self.union = make_union(self.ramon, self.carmen, children=[self.javier])

    def test_link_is_biological_by_default(self):
        self.assertEqual(self.union.child_links.get().kind, ChildLink.Kind.BIOLOGICAL)

    def test_person_can_be_a_child_in_more_than_one_union(self):
        stepfather = make_person("Luis", "Pérez", birth_date="1960")
        second_union = make_union(self.carmen, stepfather)
        link = ChildLink(union=second_union, child=self.javier, kind=ChildLink.Kind.FOSTER)
        link.full_clean()
        link.save()

        self.assertEqual(self.javier.parent_links.count(), 2)

    def test_same_child_twice_in_the_same_union_is_rejected(self):
        with self.assertRaises(ValidationError):
            ChildLink(union=self.union, child=self.javier).full_clean()

    def test_partner_cannot_be_a_child_of_their_own_union(self):
        with self.assertRaises(ValidationError) as caught:
            ChildLink(union=self.union, child=self.ramon).full_clean()

        self.assertIn("child", caught.exception.message_dict)

    def test_person_cannot_be_the_child_of_their_own_descendant(self):
        ana = make_person("Ana", "Ruiz", birth_date="1991")
        grandchild = make_person("Leo", "García", birth_date="2015")
        javier_union = make_union(self.javier, ana, children=[grandchild])
        grandchild_union = make_union(grandchild)

        for union in (javier_union, grandchild_union):
            with self.subTest(union=str(union)), self.assertRaises(ValidationError) as caught:
                ChildLink(union=union, child=self.ramon).full_clean()
            self.assertIn("child", caught.exception.message_dict)

    def test_deleting_a_union_removes_its_child_links(self):
        self.union.delete()

        self.assertEqual(ChildLink.objects.count(), 0)
        self.assertTrue(Person.objects.filter(pk=self.javier.pk).exists())

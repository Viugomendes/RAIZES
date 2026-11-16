"""The invented family in demo/: it must contain every hard case."""
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Count
from django.test import TestCase, override_settings

from family.demo import DEMO_FILE, load_demo_family, read_demo_file
from family.models import ChildLink, Person, Place, Recipe, Union


class DemoFamilyTestCase(TestCase):
    """Base class for tests that need the invented family loaded."""

    @classmethod
    def setUpTestData(cls):
        load_demo_family(with_portraits=False)


class DemoContentsTests(DemoFamilyTestCase):
    def test_central_person_matches_the_settings(self):
        data = read_demo_file()

        self.assertEqual(data["central_person"], settings.DEMO_CENTRAL_PERSON)
        self.assertEqual(data["family_name"], settings.DEMO_FAMILY_NAME)
        self.assertTrue(Person.objects.filter(identifier=settings.DEMO_CENTRAL_PERSON).exists())

    def test_every_record_is_valid(self):
        for model in (Place, Person, Union, ChildLink, Recipe):
            for record in model.objects.all():
                with self.subTest(record=str(record)):
                    record.full_clean()

    def test_family_is_big_enough_to_be_a_real_test(self):
        self.assertGreaterEqual(Person.objects.count(), 45)

    def test_one_person_has_three_unions(self):
        joaquim = Person.objects.get(identifier="joaquim-carvalho-1938")

        unions = Union.objects.filter(partner1=joaquim) | Union.objects.filter(partner2=joaquim)

        self.assertEqual(unions.count(), 3)

    def test_central_person_is_a_child_in_two_unions_one_as_foster_child(self):
        lia = Person.objects.get(identifier=settings.DEMO_CENTRAL_PERSON)

        kinds = sorted(lia.parent_links.values_list("kind", flat=True))

        self.assertEqual(kinds, ["biological", "foster"])

    def test_one_family_has_eight_siblings(self):
        biggest = Union.objects.annotate(n=Count("child_links")).order_by("-n").first()

        self.assertEqual(biggest.n, 8)

    def test_there_is_an_adoptive_child(self):
        self.assertTrue(ChildLink.objects.filter(kind=ChildLink.Kind.ADOPTIVE).exists())

    def test_there_is_a_dating_relationship(self):
        self.assertTrue(Union.objects.filter(kind=Union.Kind.DATING).exists())

    def test_there_is_a_person_with_an_unknown_father(self):
        alone = Union.objects.filter(partner2__isnull=True, child_links__isnull=False)

        self.assertTrue(alone.exists())

    def test_there_are_ended_and_current_unions(self):
        self.assertTrue(Union.objects.filter(ended=True).exists())
        self.assertTrue(Union.objects.filter(ended=False).exists())

    def test_there_are_deceased_people_with_and_without_a_known_date(self):
        self.assertTrue(Person.objects.filter(deceased=True).exclude(death_date="").exists())
        self.assertTrue(Person.objects.filter(deceased=True, death_date="").exists())

    def test_there_is_a_child(self):
        self.assertTrue(Person.objects.filter(birth_date__gte="2015").exists())

    def test_there_are_uncertain_records(self):
        self.assertTrue(Person.objects.filter(birth_date_approximate=True).exists())
        self.assertTrue(Person.objects.filter(confirmed=False).exists())
        self.assertTrue(Person.objects.filter(birth_date="").exists())

    def test_some_people_have_texts_and_an_interview(self):
        self.assertTrue(Person.objects.exclude(interview_url="").exists())
        self.assertTrue(Person.objects.exclude(childhood="").exists())
        self.assertTrue(Person.objects.exclude(remembrance="").exists())
        self.assertTrue(Union.objects.exclude(story="").exists())

    def test_most_people_have_only_the_fixed_fields(self):
        without_texts = Person.objects.filter(tastes="", childhood="", legacy="")

        self.assertGreater(without_texts.count(), Person.objects.count() / 2)


class DemoLoadingTests(TestCase):
    def test_loading_twice_does_not_duplicate_anything(self):
        first = load_demo_family(with_portraits=False)
        second = load_demo_family(with_portraits=False)

        self.assertEqual(first, second)
        self.assertEqual(Person.objects.count(), first["people"])

    def test_portraits_are_drawn_for_the_people_marked_in_the_file(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            load_demo_family(with_portraits=True)

            with_photo = Person.objects.exclude(photo="")
            self.assertGreaterEqual(with_photo.count(), 5)
            for person in with_photo:
                self.assertTrue((Path(media) / person.photo.name).is_file())

    def test_demo_file_is_inside_the_demo_folder(self):
        self.assertEqual(DEMO_FILE, Path(settings.BASE_DIR) / "demo" / "family.toml")

    @override_settings(RAIZES_DATASET="real")
    def test_command_refuses_to_touch_the_real_family(self):
        with self.assertRaises(CommandError):
            call_command("load_demo", stdout=StringIO())

        self.assertFalse(Person.objects.exists())

    @override_settings(RAIZES_DATASET="demo")
    def test_command_loads_the_family(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            output = StringIO()
            call_command("load_demo", stdout=output)

        self.assertTrue(Person.objects.filter(identifier=settings.DEMO_CENTRAL_PERSON).exists())
        self.assertIn(str(Person.objects.count()), output.getvalue())

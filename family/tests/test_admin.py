"""The admin panel: where the owner fills in the family, on their own computer."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from family.models import ChildLink, Person, Union

from .test_models import make_person, make_union

PERSON_FORM = {
    "given_name": "Ramón",
    "surname": "García Ortega",
    "nickname": "El Moncho",
    "other_names": "",
    "sex": "m",
    "identifier": "",
    "birth_date": "14/03/1962",
    "death_date": "",
    "occupation": "carpinteiro",
    "tags": "músico, emigrante",
    "interview_url": "",
    "confirmed": "on",
    "source": "contado pela tia Marta",
    "tastes": "",
    "childhood": "",
    "work": "",
    "love": "",
    "origins": "",
    "memories": "",
    "legacy": "",
    "remembrance": "",
}


def inline_children(*rows, initial=0):
    """Form data of the "children" table inside the union form."""
    data = {
        "child_links-TOTAL_FORMS": str(len(rows)),
        "child_links-INITIAL_FORMS": str(initial),
        "child_links-MIN_NUM_FORMS": "0",
        "child_links-MAX_NUM_FORMS": "1000",
    }
    for index, (child, kind) in enumerate(rows):
        data[f"child_links-{index}-child"] = str(child.pk)
        data[f"child_links-{index}-kind"] = kind
    return data


class AdminTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_superuser("owner", password="x")

    def setUp(self):
        self.client.force_login(self.owner)


class PersonAdminTests(AdminTestCase):
    def test_admin_is_in_portuguese_by_default(self):
        response = self.client.get("/admin/family/person/add/")

        self.assertContains(response, "Adicionar pessoa")
        self.assertContains(response, "Data de nascimento")

    def test_person_can_be_added(self):
        response = self.client.post("/admin/family/person/add/", PERSON_FORM)

        self.assertRedirects(response, "/admin/family/person/")
        person = Person.objects.get()
        self.assertEqual(person.identifier, "ramon-garcia-1962")
        self.assertEqual(person.birth_date, "1962-03-14")
        self.assertEqual(person.tag_list, ["músico", "emigrante"])

    def test_invalid_date_shows_an_error_in_portuguese(self):
        response = self.client.post(
            "/admin/family/person/add/", {**PERSON_FORM, "birth_date": "31/02/1962"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Escreva a data como DD/MM/AAAA ou só o ano (AAAA).")
        self.assertFalse(Person.objects.exists())

    def test_repeated_identifier_shows_an_error(self):
        make_person(identifier="ramon-garcia-1962")

        response = self.client.post(
            "/admin/family/person/add/", {**PERSON_FORM, "identifier": "ramon-garcia-1962"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "errorlist")
        self.assertEqual(Person.objects.count(), 1)

    def test_identifier_can_be_typed_only_when_creating(self):
        person = make_person(birth_date="1962")

        add_page = self.client.get("/admin/family/person/add/")
        change_page = self.client.get(f"/admin/family/person/{person.pk}/change/")

        self.assertContains(add_page, 'name="identifier"')
        self.assertNotContains(change_page, 'name="identifier"')
        self.assertContains(change_page, "ramon-garcia-1962")

    def test_editing_a_person_keeps_the_identifier(self):
        person = make_person(birth_date="1962")

        response = self.client.post(
            f"/admin/family/person/{person.pk}/change/",
            {**PERSON_FORM, "given_name": "Raimundo", "birth_date": "1963"},
        )

        self.assertRedirects(response, "/admin/family/person/")
        person.refresh_from_db()
        self.assertEqual(person.given_name, "Raimundo")
        self.assertEqual(person.identifier, "ramon-garcia-1962")

    def test_people_can_be_searched_by_name(self):
        make_person(birth_date="1962")
        make_person("Carmen", "López")

        response = self.client.get("/admin/family/person/?q=carmen")

        self.assertContains(response, "Carmen López")
        self.assertNotContains(response, "Ramón García")


class UnionAdminTests(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.ramon = make_person(birth_date="1962")
        self.carmen = make_person("Carmen", "López", birth_date="1964")
        self.javier = make_person("Javier", "García", birth_date="1990")
        self.form = {
            "partner1": str(self.ramon.pk),
            "partner2": str(self.carmen.pk),
            "kind": "marriage",
            "start_date": "1988",
            "end_date": "",
            "story": "Conheceram-se em um baile.",
        }

    def test_union_with_a_child_can_be_added(self):
        response = self.client.post(
            "/admin/family/union/add/",
            {**self.form, **inline_children((self.javier, "biological"))},
        )

        self.assertRedirects(response, "/admin/family/union/")
        union = Union.objects.get()
        self.assertEqual(union.partners, [self.ramon, self.carmen])
        link = union.child_links.get()
        self.assertEqual((link.child, link.kind), (self.javier, "biological"))

    def test_union_with_an_unknown_partner_can_be_added(self):
        response = self.client.post(
            "/admin/family/union/add/",
            {**self.form, "partner2": "", **inline_children((self.javier, "foster"))},
        )

        self.assertRedirects(response, "/admin/family/union/")
        self.assertIsNone(Union.objects.get().partner2)
        self.assertEqual(ChildLink.objects.get().kind, "foster")

    def test_same_person_twice_shows_an_error_in_portuguese(self):
        response = self.client.post(
            "/admin/family/union/add/",
            {**self.form, "partner2": str(self.ramon.pk), **inline_children()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uma união precisa de duas pessoas diferentes.")
        self.assertFalse(Union.objects.exists())

    def test_partner_as_their_own_child_shows_an_error(self):
        response = self.client.post(
            "/admin/family/union/add/",
            {**self.form, **inline_children((self.ramon, "biological"))},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Uma pessoa não pode ser filha da própria união.")
        self.assertFalse(Union.objects.exists())

    def test_same_child_twice_shows_an_error(self):
        response = self.client.post(
            "/admin/family/union/add/",
            {
                **self.form,
                **inline_children((self.javier, "biological"), (self.javier, "adoptive")),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Union.objects.exists())

    def test_ancestor_as_child_shows_an_error_when_editing(self):
        make_union(self.ramon, self.carmen, children=[self.javier])
        javier_union = make_union(self.javier)

        response = self.client.post(
            f"/admin/family/union/{javier_union.pk}/change/",
            {
                "partner1": str(self.javier.pk),
                "partner2": "",
                "kind": "",
                "start_date": "",
                "end_date": "",
                "story": "",
                **inline_children((self.ramon, "biological")),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "é antepassada de um dos parceiros")
        self.assertFalse(javier_union.child_links.exists())


class AdminSiteTests(AdminTestCase):
    def test_every_model_has_a_list_page(self):
        for name in ("person", "union", "place", "photo", "recipe"):
            with self.subTest(model=name):
                self.assertEqual(self.client.get(f"/admin/family/{name}/").status_code, 200)
                self.assertEqual(self.client.get(f"/admin/family/{name}/add/").status_code, 200)

    def test_header_says_which_family_is_loaded(self):
        response = self.client.get("/admin/")

        self.assertContains(response, "família inventada")

    def test_admin_needs_a_login(self):
        self.client.logout()

        response = self.client.get("/admin/family/person/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

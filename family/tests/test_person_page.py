"""The page of a person, with its 10 sections, and the list of people."""
import re
import tempfile

from django.test import override_settings

from family.demo import load_demo_family
from family.models import Person
from family.textcheck import all_text_problems

from .test_demo import DemoFamilyTestCase


def section(html: str, section_id: str) -> str:
    """The HTML of one <section id="..."> of the page ("" when absent)."""
    match = re.search(rf'<section id="{section_id}".*?</section>', html, re.DOTALL)
    return match.group(0) if match else ""


def row(html: str, label: str) -> str:
    """The value of one row of the "basic data" table ("" when absent)."""
    match = re.search(rf"<dt>{re.escape(label)}</dt>\s*<dd>(.*?)</dd>", html, re.DOTALL)
    return match.group(1) if match else ""


class PersonPageTestCase(DemoFamilyTestCase):
    def page(self, identifier: str, language: str = "pt-br") -> str:
        response = self.client.get(f"/{language}/people/{identifier}/")
        self.assertEqual(response.status_code, 200)
        return response.content.decode()


class PersonHeaderTests(PersonPageTestCase):
    def test_header_shows_name_nickname_years_place_and_occupation(self):
        html = self.page("lia-carvalho-1996")
        header = re.search(r'<header class="person-header">.*?</header>', html, re.DOTALL).group(0)

        self.assertIn("<h1>Lia Figueira Carvalho</h1>", header)
        self.assertIn("Lili", header)
        self.assertIn("1996", header)
        self.assertIn("Curitiba, Brasil", header)
        self.assertIn("ilustradora", header)

    def test_person_without_photo_shows_their_initials(self):
        html = self.page("lia-carvalho-1996")

        self.assertIn('class="avatar avatar-initials"', html)
        self.assertNotIn("<img class=\"avatar\"", html)

    def test_unknown_person_is_a_404(self):
        response = self.client.get("/pt-br/people/nobody-here-1900/")

        self.assertEqual(response.status_code, 404)

    def test_unconfirmed_person_is_marked(self):
        self.assertIn("ainda não foram confirmadas", self.page("maria-jacaranda-1"))
        self.assertNotIn("ainda não foram confirmadas", self.page("lia-carvalho-1996"))

    def test_every_person_has_a_page(self):
        for identifier in Person.objects.values_list("identifier", flat=True):
            with self.subTest(person=identifier):
                self.page(identifier)
                self.page(identifier, language="es")


class PersonPhotoTests(DemoFamilyTestCase):
    def test_person_with_photo_shows_it(self):
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            load_demo_family(with_portraits=True)

            html = self.client.get("/pt-br/people/lia-carvalho-1996/").content.decode()

        self.assertIn('<img class="avatar" src="/media/people/lia-carvalho-1996.png"', html)
        self.assertNotIn("avatar-initials", html)


class BasicDataTests(PersonPageTestCase):
    def test_birth_date_and_place(self):
        basic = section(self.page("lia-carvalho-1996"), "basic-data")

        self.assertIn("12 de maio de 1996", row(basic, "Nascimento"))
        self.assertIn("São Paulo, Brasil", row(basic, "Nascimento"))

    def test_living_person_shows_where_they_live_and_no_death(self):
        basic = section(self.page("lia-carvalho-1996"), "basic-data")

        self.assertIn("Curitiba, Brasil", row(basic, "Mora em"))
        self.assertEqual(row(basic, "Falecimento"), "")

    def test_deceased_person_shows_death_and_resting_place(self):
        basic = section(self.page("anselmo-figueira-1940"), "basic-data")

        self.assertIn("8 de janeiro de 2015", row(basic, "Falecimento"))
        self.assertIn("Ouro Preto, Brasil", row(basic, "Descansa em"))
        self.assertEqual(row(basic, "Mora em"), "")

    def test_deceased_person_without_a_date(self):
        basic = section(self.page("maria-jacaranda-1"), "basic-data")

        self.assertIn("data desconhecida", row(basic, "Falecimento"))

    def test_approximate_date(self):
        basic = section(self.page("teodoro-figueira-1885"), "basic-data")

        self.assertIn("c. 1885", row(basic, "Nascimento"))

    def test_three_parental_figures_with_links(self):
        parents = row(section(self.page("lia-carvalho-1996"), "basic-data"), "Pais")

        self.assertIn('href="/pt-br/people/helena-figueira-1970/"', parents)
        self.assertIn('href="/pt-br/people/tomas-carvalho-1968/"', parents)
        self.assertIn('href="/pt-br/people/rui-pinheiro-1965/"', parents)
        self.assertEqual(parents.count("de criação"), 1)

    def test_person_with_an_unknown_father_shows_one_parent(self):
        parents = row(section(self.page("rui-pinheiro-1965"), "basic-data"), "Pais")

        self.assertEqual(parents.count("<a "), 1)
        self.assertIn("Zélia Pinheiro", parents)

    def test_person_without_known_parents_has_no_parents_row(self):
        basic = section(self.page("davi-amoreira-1995"), "basic-data")

        self.assertEqual(row(basic, "Pais"), "")

    def test_full_half_and_step_siblings_are_listed_separately(self):
        basic = section(self.page("lia-carvalho-1996"), "basic-data")

        self.assertIn("Bento Figueira Carvalho", row(basic, "Irmãos"))
        self.assertNotIn("Nina", row(basic, "Irmãos"))
        self.assertIn("Nina Figueira Pinheiro", row(basic, "Meio-irmãos"))
        self.assertIn("Otávio Macieira Pinheiro", row(basic, "Irmãos de criação"))

    def test_eight_siblings(self):
        siblings = row(section(self.page("helena-figueira-1970"), "basic-data"), "Irmãos")

        self.assertEqual(siblings.count("<a "), 7)

    def test_three_unions_with_their_children(self):
        unions = row(section(self.page("joaquim-carvalho-1938"), "basic-data"), "Uniões")

        self.assertEqual(unions.count('<li class="union"'), 3)
        self.assertIn("Amélia Castanheira", unions)
        self.assertIn("Lúcia Laranjeira", unions)
        self.assertIn("Sônia Cerejeira", unions)
        self.assertIn("Gabriel Cerejeira Carvalho", unions)
        self.assertIn("1982–1995", unions)
        self.assertIn("desde 1998", unions)

    def test_union_ends_with_the_death_of_a_partner_without_being_marked_as_ended(self):
        unions = row(section(self.page("joaquim-carvalho-1938"), "basic-data"), "Uniões")
        with_amelia = unions.split('<li class="union"')[1]

        self.assertIn("1962–1979", with_amelia)
        self.assertNotIn("desde", with_amelia)
        self.assertNotIn("terminou", with_amelia)

    def test_union_with_a_partner_who_died_on_an_unknown_date(self):
        unions = row(section(self.page("teodoro-figueira-1885"), "basic-data"), "Uniões")

        self.assertNotIn("desde", unions)

    def test_ended_union_is_marked_and_current_union_is_not(self):
        unions = row(section(self.page("helena-figueira-1970"), "basic-data"), "Uniões")
        first, second = unions.split('<li class="union"')[1:]

        self.assertIn("Tomás", first)
        self.assertIn("terminou", first)
        self.assertIn("Rui", second)
        self.assertNotIn("terminou", second)

    def test_dating_relationship(self):
        unions = row(section(self.page("lia-carvalho-1996"), "basic-data"), "Uniões")

        self.assertIn("Namoro", unions)
        self.assertIn("Davi Amoreira", unions)

    def test_union_with_an_unknown_partner_lists_the_children(self):
        unions = row(section(self.page("zelia-pinheiro-1942"), "basic-data"), "Uniões")

        self.assertIn("desconhecido", unions)
        self.assertIn("Rui Pinheiro", unions)

    def test_adopted_child_is_marked_on_both_pages(self):
        marta = row(section(self.page("marta-figueira-1966"), "basic-data"), "Uniões")
        jonas = row(section(self.page("jonas-nogueira-2001"), "basic-data"), "Pais")

        self.assertEqual(marta.count("por adoção"), 1)
        self.assertEqual(jonas.count("por adoção"), 2)

    def test_foster_children_are_listed_with_the_union_that_raised_them(self):
        unions = row(section(self.page("rui-pinheiro-1965"), "basic-data"), "Uniões")

        self.assertIn("Lia Figueira Carvalho", unions)
        self.assertEqual(unions.count("de criação"), 2)

    def test_grandchildren(self):
        basic = section(self.page("joaquim-carvalho-1938"), "basic-data")

        self.assertEqual(row(basic, "Netos").count("<a "), 4)
        self.assertEqual(row(section(self.page("lia-carvalho-1996"), "basic-data"), "Netos"), "")

    def test_source_and_tags(self):
        basic = section(self.page("lia-carvalho-1996"), "basic-data")

        self.assertIn("ela mesma", row(basic, "Fonte"))
        self.assertIn("artista", row(basic, "Etiquetas"))


class TextSectionsTests(PersonPageTestCase):
    def test_section_with_text_appears_with_its_title(self):
        html = self.page("lia-carvalho-1996")

        self.assertIn("<h2>Gostos e manias</h2>", section(html, "tastes"))
        self.assertIn("<h2>Infância e juventude</h2>", section(html, "childhood"))
        self.assertIn("<h2>Legado</h2>", section(html, "legacy"))

    def test_empty_section_does_not_appear(self):
        html = self.page("lia-carvalho-1996")

        for empty in ("work", "origins", "memories", "remembrance"):
            with self.subTest(section=empty):
                self.assertEqual(section(html, empty), "")

    def test_child_with_only_basic_data_has_a_single_section(self):
        html = self.page("theo-carvalho-2021")

        self.assertEqual(html.count("<section id="), 1)
        self.assertNotEqual(section(html, "basic-data"), "")

    def test_sections_appear_in_the_order_of_the_plan(self):
        html = self.page("helena-figueira-1970")

        found = re.findall(r'<section id="([\w-]+)"', html)

        self.assertEqual(found, ["basic-data", "childhood", "work", "love", "memories", "gallery"])

    def test_links_in_the_text_lead_to_the_other_person(self):
        childhood = section(self.page("lia-carvalho-1996"), "childhood")

        self.assertIn(
            '<a class="person-link" href="/pt-br/people/bento-carvalho-1993/">meu irmão Bento</a>',
            childhood,
        )
        self.assertIn("Helena Oliveira Figueira</a>", childhood)

    def test_story_of_the_couple_appears_on_both_pages(self):
        for identifier in ("helena-figueira-1970", "tomas-carvalho-1968"):
            with self.subTest(person=identifier):
                self.assertIn("festa junina", section(self.page(identifier), "love"))

    def test_love_section_has_one_block_per_union_with_a_story(self):
        love = section(self.page("joaquim-carvalho-1938"), "love")

        self.assertEqual(love.count('class="union-story"'), 2)
        self.assertIn("Casei três vezes", love)

    def test_section_for_those_who_died_is_remembered_by_others(self):
        html = self.page("anselmo-figueira-1940")

        self.assertIn("<h2>Na memória dos outros</h2>", section(html, "remembrance"))
        self.assertIn("assobiava", section(html, "remembrance"))

    def test_content_is_not_translated_but_the_interface_is(self):
        html = self.page("lia-carvalho-1996", language="es")

        self.assertIn("<h2>Gustos y manías</h2>", html)
        self.assertIn("Hermanos", html)
        self.assertIn("meu irmão Bento", html)
        self.assertIn('href="/es/people/bento-carvalho-1993/"', html)


class GallerySectionTests(PersonPageTestCase):
    def test_interview_is_embedded_without_cookies(self):
        gallery = section(self.page("helena-figueira-1970"), "gallery")

        self.assertIn('src="https://www.youtube-nocookie.com/embed/aqz-KE-bpKQ"', gallery)
        self.assertIn('href="https://www.youtube.com/watch?v=aqz-KE-bpKQ"', gallery)

    def test_minutes_in_the_text_link_to_the_interview(self):
        childhood = section(self.page("helena-figueira-1970"), "childhood")

        self.assertIn('data-seconds="42"', childhood)
        self.assertIn('data-seconds="195"', childhood)

    def test_places_where_the_person_lived(self):
        gallery = section(self.page("helena-figueira-1970"), "gallery")

        for place in ("Ouro Preto, Brasil", "São Paulo, Brasil", "Curitiba, Brasil"):
            with self.subTest(place=place):
                self.assertIn(place, gallery)

    def test_person_without_interview_or_places_has_no_gallery_section(self):
        self.assertEqual(section(self.page("theo-carvalho-2021"), "gallery"), "")

    def test_page_without_interview_loads_nothing_from_youtube(self):
        self.assertNotIn("youtube", self.page("lia-carvalho-1996"))


class PersonListTests(PersonPageTestCase):
    def test_list_links_to_every_person(self):
        html = self.client.get("/pt-br/people/").content.decode()

        for identifier in Person.objects.values_list("identifier", flat=True):
            with self.subTest(person=identifier):
                self.assertIn(f'href="/pt-br/people/{identifier}/"', html)

    def test_list_is_alphabetical_ignoring_accents(self):
        html = self.client.get("/pt-br/people/").content.decode()
        names = re.findall(r'<a href="/pt-br/people/[\w-]+/">([^<]+)</a>', html)

        self.assertLess(names.index("Alice Videira Loureiro"), names.index("Álvaro Oliveira Figueira"))
        self.assertLess(names.index("Álvaro Oliveira Figueira"), names.index("Amélia Castanheira"))
        self.assertLess(names.index("Inês Oliveira Figueira"), names.index("Íris Salgueiro"))
        self.assertLess(names.index("Íris Salgueiro"), names.index("Jandira Mangueira"))

    def test_list_shows_the_years(self):
        html = self.client.get("/pt-br/people/").content.decode()

        self.assertIn("1940–2015", html)


class DemoTextsTests(DemoFamilyTestCase):
    def test_invented_family_has_no_broken_links(self):
        self.assertEqual(all_text_problems(), [])

    def test_broken_link_is_reported_with_the_person_and_the_section(self):
        lia = Person.objects.get(identifier="lia-carvalho-1996")
        lia.work = "Trabalhei com [[ninguem-silva-1900]]."
        lia.save()

        problems = all_text_problems()

        self.assertEqual(len(problems), 1)
        self.assertIn("Lia Figueira Carvalho", problems[0])
        self.assertIn("Trabalho e vida adulta", problems[0])
        self.assertIn("[[ninguem-silva-1900]]", problems[0])

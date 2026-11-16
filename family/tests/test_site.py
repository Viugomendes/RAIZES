"""The skeleton of the site: languages, header and the language selector."""
from django.test import TestCase, override_settings


class SiteSkeletonTests(TestCase):
    def test_root_address_redirects_to_the_default_language(self):
        response = self.client.get("/")

        self.assertRedirects(response, "/pt-br/")

    def test_home_page_opens_in_portuguese(self):
        response = self.client.get("/pt-br/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html lang="pt-br"')

    def test_home_page_opens_in_spanish(self):
        response = self.client.get("/es/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<html lang="es"')

    def test_language_selector_links_to_the_same_page_in_the_other_language(self):
        response = self.client.get("/pt-br/people/")

        self.assertContains(response, 'href="/es/people/"')

    @override_settings(RAIZES_FAMILY_NAME="Família Teste")
    def test_family_name_appears_in_the_header(self):
        response = self.client.get("/pt-br/")

        self.assertContains(response, "Família Teste")

    def test_pages_ask_search_engines_not_to_index_them(self):
        response = self.client.get("/pt-br/")

        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_pages_load_nothing_from_other_servers(self):
        response = self.client.get("/pt-br/")
        html = response.content.decode()

        self.assertNotIn('src="http', html)
        self.assertNotIn('href="http', html)
        self.assertNotIn("//cdn", html)

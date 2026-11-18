"""The skeleton of the site: languages, header and the language selector."""
import re

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
        response = self.client.get("/pt-br/search/")

        self.assertContains(response, 'href="/es/search/"')

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


def without_lazy_scripts(html: str) -> str:
    """The page without the scripts kept for later (the search in place)."""
    return re.sub(r'<template id="quick-search-scripts">.*?</template>', "", html, flags=re.DOTALL)


def site_nav(html: str) -> str:
    return re.search(r'<nav class="site-nav".*?</nav>', html, re.DOTALL).group(0)


class HeaderTests(TestCase):
    """The thin header: icons with names, one flag, the theme and the search."""

    def html(self, path: str) -> str:
        return self.client.get(path).content.decode()

    def test_one_flag_of_the_current_language_links_to_the_other_one(self):
        html = self.html("/pt-br/search/")
        flags = re.findall(r'<a class="flag[^"]*"[^>]*>', html)

        self.assertEqual(len(flags), 1)
        self.assertIn('href="/es/search/"', flags[0])
        self.assertIn('lang="es"', flags[0])
        self.assertIn('hreflang="es"', flags[0])
        # Said in the language it leads to, so its readers understand it.
        self.assertIn('aria-label="Cambiar idioma a Español"', flags[0])
        self.assertIn('title="Cambiar idioma a Español"', flags[0])
        flag = re.search(r'<a class="flag[^"]*".*?</a>', html, re.DOTALL).group(0)
        self.assertIn("#009b3a", flag)  # the Brazilian flag: the page is in Portuguese

    def test_flag_on_a_spanish_page(self):
        flag = re.search(r'<a class="flag[^"]*".*?</a>', self.html("/es/tree/"), re.DOTALL).group(0)

        self.assertIn('href="/pt-br/tree/"', flag)
        self.assertIn('aria-label="Mudar idioma para Português"', flag)
        self.assertIn('lang="pt-br"', flag)
        self.assertIn("#c60b1e", flag)

    def test_current_page_is_marked_in_the_navigation(self):
        for path, current in (("/pt-br/", "Novidades"), ("/pt-br/tree/", "Árvore"), ("/pt-br/search/", "Busca")):
            with self.subTest(page=path):
                nav = site_nav(self.html(path))
                marked = re.findall(r'<a [^>]*aria-current="page"[^>]*>.*?</a>', nav, re.DOTALL)
                self.assertEqual(len(marked), 1)
                self.assertIn(current, marked[0])

    def test_navigation_has_news_tree_and_the_magnifier(self):
        nav = site_nav(self.html("/es/"))
        links = re.findall(r'<a ([^>]*)>(.*?)</a>', nav, re.DOTALL)

        self.assertEqual(
            [re.search(r'href="([^"]+)"', attributes).group(1) for attributes, _ in links],
            ["/es/", "/es/tree/", "/es/search/"],
        )
        self.assertIn('class="nav-search"', links[2][0])
        for attributes, inside in links:
            # An icon the screen reader skips, and the name in words.
            self.assertIn('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"', inside)
            self.assertRegex(inside, r'<span class="nav-label">[^<]+</span>')
        self.assertEqual(
            [re.search(r'<span class="nav-label">([^<]+)</span>', inside).group(1) for _, inside in links],
            ["Novedades", "Árbol", "Búsqueda"],
        )

    def test_theme_script_runs_in_the_head_before_the_page_is_drawn(self):
        html = self.html("/pt-br/")
        head = html.split("</head>")[0]

        self.assertIn('<script src="/static/js/theme.js"></script>', head)
        self.assertLess(head.index("js/theme.js"), head.index("css/site.css"))

    def test_theme_button_says_the_current_theme(self):
        html = self.html("/pt-br/")
        button = re.search(r'<button type="button" class="theme-toggle[^"]*".*?</button>', html, re.DOTALL).group(0)
        self.assertIn('title="Mudar o tema"', button)

        for label in (
            "Mudar o tema (agora: automático)",
            "Mudar o tema (agora: claro)",
            "Mudar o tema (agora: escuro)",
        ):
            self.assertIn(label, button)

    def test_search_in_place_is_a_combobox_that_loads_the_data_only_when_opened(self):
        html = self.html("/pt-br/tree/")
        panel = re.search(r'<div class="quick-search".*?</p>\s*</div>', html, re.DOTALL).group(0)

        self.assertIn("hidden", panel.split(">")[0])
        self.assertRegex(panel, r'<input[^>]*role="combobox"[^>]*aria-expanded="false"[^>]*aria-controls="quick-search-list"')
        self.assertIn('<ul id="quick-search-list" role="listbox"', panel)
        # Messages ("nobody with this name") are outside the listbox, which holds only options.
        self.assertRegex(panel, r'<div class="quick-results" hidden>\s*<p class="quick-empty" hidden></p>\s*<ul id="quick-search-list" role="listbox"[^>]*></ul>')
        self.assertIn('aria-live="polite"', panel)
        # The data comes later, from the browser, and is not loaded with the page.
        self.assertNotIn('src="/data/family.js"', without_lazy_scripts(html))
        scripts = re.search(r'<template id="quick-search-scripts">(.*?)</template>', html, re.DOTALL).group(1)
        self.assertIn('src="/data/family.js"', scripts)
        self.assertIn('src="/static/js/search.js"', scripts)
        self.assertIn('id="header-strings"', html)
        self.assertIn('src="/static/js/header.js" defer', html)

    def test_password_page_follows_the_chosen_theme(self):
        from django.template.loader import render_to_string
        from django.test import RequestFactory

        html = render_to_string("access/enter.html", {"enter_languages": []}, request=RequestFactory().get("/entrar/"))
        # The same theme button as the site, so the choice can be made there too.
        self.assertIn('<button type="button" class="theme-toggle header-button" title="Mudar o tema">', html)
        self.assertIn("Mudar o tema (agora: escuro)", html)

        self.assertIn('<script src="/static/js/theme.js"></script>', html.split("</head>")[0])

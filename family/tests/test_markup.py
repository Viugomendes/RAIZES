"""Texts of the pages: Markdown, [[links]] and [mm:ss] interview minutes."""
from django.test import SimpleTestCase

from family.markup import LinkTargets, render_text

TARGETS = LinkTargets(
    people={"ramon-garcia-1962": "Ramón García Ortega", "marta-garcia-1964": "Marta García"},
    places={"valencia": "Valência, Espanha"},
    recipes={"feijoada-da-vo": "Feijoada da vó"},
)
VIDEO = "dQw4w9WgXcQ"


def render(text, video_id=None):
    return render_text(text, TARGETS, video_id=video_id)


class MarkdownTests(SimpleTestCase):
    def test_empty_text_gives_nothing(self):
        result = render("")

        self.assertEqual(result.html, "")
        self.assertEqual(result.problems, [])

    def test_bold_and_paragraphs(self):
        html = render("Comida favorita: **feijoada**.\n\nTime: Santos.").html

        self.assertIn("<strong>feijoada</strong>", html)
        self.assertEqual(html.count("<p>"), 2)

    def test_a_line_break_in_the_text_is_a_line_break_on_the_page(self):
        self.assertIn("<br", render("primeira linha\nsegunda linha").html)

    def test_normal_markdown_link_to_another_site(self):
        html = render("[o museu](https://example.com/museu)").html

        self.assertIn('<a href="https://example.com/museu">o museu</a>', html)

    def test_html_typed_in_the_text_is_shown_as_text(self):
        html = render("antes <script>alert(1)</script> depois\n\n<div>bloco</div>").html

        self.assertNotIn("<script>", html)
        self.assertNotIn("<div>", html)
        self.assertIn("&lt;script&gt;", html)


class PersonLinkTests(SimpleTestCase):
    def test_identifier_becomes_a_link_with_the_full_name(self):
        result = render("Brincava com [[marta-garcia-1964]].")

        self.assertIn(
            '<a class="person-link" href="/pt-br/people/marta-garcia-1964/">Marta García</a>',
            result.html,
        )
        self.assertEqual(result.problems, [])

    def test_link_with_a_chosen_text(self):
        html = render("Brincava com [[marta-garcia-1964|a irmã Marta]].").html

        self.assertIn('href="/pt-br/people/marta-garcia-1964/">a irmã Marta</a>', html)

    def test_spaces_around_the_identifier_are_ignored(self):
        html = render("[[ marta-garcia-1964 | a irmã ]]").html

        self.assertIn('href="/pt-br/people/marta-garcia-1964/">a irmã</a>', html)

    def test_chosen_text_cannot_inject_html(self):
        html = render("[[marta-garcia-1964|<b>Marta</b>]]").html

        self.assertNotIn("<b>", html)

    def test_link_to_someone_who_does_not_exist_is_a_clear_problem(self):
        result = render("Casou com [[fulano-silva-1900]].")

        self.assertEqual(len(result.problems), 1)
        self.assertIn("[[fulano-silva-1900]]", result.problems[0])
        self.assertNotIn("<a ", result.html)
        self.assertIn('class="broken-link"', result.html)
        self.assertIn("[[fulano-silva-1900]]", result.html)

    def test_two_links_in_the_same_line(self):
        html = render("[[ramon-garcia-1962]] e [[marta-garcia-1964]]").html

        self.assertEqual(html.count('class="person-link"'), 2)

    def test_link_inside_code_is_left_alone(self):
        html = render("Escreva `[[marta-garcia-1964]]` para criar um link.").html

        self.assertNotIn("person-link", html)
        self.assertIn("[[marta-garcia-1964]]", html)


class PlaceAndRecipeLinkTests(SimpleTestCase):
    def test_place_shows_its_name(self):
        result = render("Nasceu em [[lugar:valencia]].")

        self.assertIn('<span class="place-name">Valência, Espanha</span>', result.html)
        self.assertEqual(result.problems, [])

    def test_place_with_a_chosen_text(self):
        html = render("Voltou à [[lugar:valencia|terra natal]].").html

        self.assertIn('<span class="place-name">terra natal</span>', html)

    def test_recipe_shows_its_title(self):
        html = render("Fazia a [[receita:feijoada-da-vo]].").html

        self.assertIn('<span class="recipe-name">Feijoada da vó</span>', html)

    def test_spanish_and_english_prefixes_are_accepted(self):
        html = render("[[receta:feijoada-da-vo]] [[recipe:feijoada-da-vo]] [[place:valencia]]").html

        self.assertEqual(html.count('class="recipe-name"'), 2)
        self.assertEqual(html.count('class="place-name"'), 1)

    def test_place_that_does_not_exist_is_a_problem(self):
        result = render("[[lugar:atlantida]]")

        self.assertEqual(len(result.problems), 1)
        self.assertIn("[[lugar:atlantida]]", result.problems[0])
        self.assertIn('class="broken-link"', result.html)

    def test_recipe_that_does_not_exist_is_a_problem(self):
        result = render("[[receita:bolo-invisivel]]")

        self.assertEqual(len(result.problems), 1)
        self.assertIn("[[receita:bolo-invisivel]]", result.problems[0])


class InterviewMinuteTests(SimpleTestCase):
    def test_minute_becomes_a_link_to_that_moment_of_the_video(self):
        result = render("A primeira lembrança é a do quintal. [04:12]", video_id=VIDEO)

        self.assertIn(
            '<a class="timestamp" data-seconds="252" '
            'href="https://www.youtube.com/watch?v=dQw4w9WgXcQ&amp;t=252s">04:12</a>',
            result.html,
        )
        self.assertEqual(result.problems, [])

    def test_hours_minutes_and_seconds(self):
        html = render("[1:02:03]", video_id=VIDEO).html

        self.assertIn('data-seconds="3723"', html)

    def test_minutes_above_fifty_nine(self):
        html = render("[75:10]", video_id=VIDEO).html

        self.assertIn('data-seconds="4510"', html)

    def test_minute_without_an_interview_is_a_problem(self):
        result = render("Lembro do quintal. [04:12]")

        self.assertEqual(len(result.problems), 1)
        self.assertIn("[04:12]", result.problems[0])
        self.assertNotIn("<a ", result.html)
        self.assertIn("[04:12]", result.html)

    def test_normal_link_whose_text_looks_like_a_minute_is_left_alone(self):
        result = render("[04:12](https://example.com/)", video_id=VIDEO)

        self.assertIn('<a href="https://example.com/">04:12</a>', result.html)
        self.assertNotIn("timestamp", result.html)

    def test_other_text_in_brackets_is_left_alone(self):
        result = render("Ele dizia [sic] que sim. [12:99]", video_id=VIDEO)

        self.assertNotIn("timestamp", result.html)
        self.assertEqual(result.problems, [])


class SeveralProblemsTests(SimpleTestCase):
    def test_every_problem_is_reported_in_order(self):
        result = render("[[ninguem-1]] depois [[lugar:nenhum]] e [00:10]")

        self.assertEqual(len(result.problems), 3)
        self.assertIn("ninguem-1", result.problems[0])
        self.assertIn("lugar:nenhum", result.problems[1])
        self.assertIn("00:10", result.problems[2])

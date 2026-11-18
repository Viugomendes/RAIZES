"""The scripts that run in the browser, tested with Node.

They are skipped when Node is not installed.
"""
import datetime
import json
import shutil
import subprocess
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase

from family.graph import load_family_graph
from family.kinship import CENTER
from family.site_data import build_site_data

from .base import DemoFamilyTestCase

NODE = shutil.which("node")
RUNNER = Path(__file__).parent / "js" / "run.js"


def day(text: str) -> dict:
    value = datetime.date.fromisoformat(text)
    return {"y": value.year, "m": value.month, "d": value.day}


@skipUnless(NODE, "Node is not installed")
class JavaScriptTestCase(DemoFamilyTestCase):
    def setUp(self):
        self.data = build_site_data(today=datetime.date(2026, 11, 17))

    def run_js(self, task: str, **arguments):
        request = json.dumps({"task": task, "data": self.data, **arguments})
        completed = subprocess.run(
            [NODE, str(RUNNER)], input=request, capture_output=True, text=True, encoding="utf-8", check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)


@skipUnless(NODE, "Node is not installed")
class PasswordFunctionTests(SimpleTestCase):
    """The Cloudflare function that asks for the family password."""

    def test_password_function_tests_pass(self):
        tests = Path(__file__).parent / "js" / "middleware.test.mjs"
        completed = subprocess.run(
            [NODE, "--test", str(tests)], capture_output=True, text=True, encoding="utf-8", check=False
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("fail 0", completed.stdout)


class KinshipInTheBrowserTests(JavaScriptTestCase):
    def test_same_results_as_python_for_every_central_person(self):
        graph = load_family_graph()
        browser = self.run_js("kinship")

        for person in graph.people:
            with self.subTest(central=person):
                result = browser[person]
                self.assertEqual(result["distance"], graph.distances(person))
                self.assertEqual(result["generation"], graph.generations(person))
                self.assertEqual(result["side"], graph.sides(person))
                self.assertEqual(result["figures"], graph.parental_figures(person))

    def test_center_has_the_same_name(self):
        browser = self.run_js("kinship")

        self.assertEqual(browser["lia-carvalho-1996"]["side"]["bento-carvalho-1993"], CENTER)


class MuralTests(JavaScriptTestCase):
    def mural(self, *dates):
        return self.run_js("mural", days=[day(text) for text in dates])

    def test_photo_taken_on_this_day_in_another_year(self):
        (result,) = self.mural("2026-11-18")
        photo = next(p for p in self.data["photos"] if p["caption"] == "Casamento de Anselmo e Dalva")

        self.assertIn({"kind": "photo", "photo": photo["id"], "years": 65}, result["onThisDay"])

    def test_birthdays_of_the_week_only_for_the_living(self):
        (result,) = self.mural("2026-05-10")
        week = {(entry["person"], entry["years"]) for entry in result["week"]}

        self.assertIn(("lia-carvalho-1996", 30), week)  # 12 May
        self.assertTrue(all(not self.person(person)["deceased"] for person, _years in week))

    def test_today_is_marked_in_the_week(self):
        (result,) = self.mural("2026-05-12")
        lia = next(entry for entry in result["week"] if entry["person"] == "lia-carvalho-1996")

        self.assertTrue(lia["isToday"])

    def test_week_ends_after_seven_days(self):
        early, late = self.mural("2026-05-06", "2026-05-05")

        self.assertIn("lia-carvalho-1996", [entry["person"] for entry in early["week"]])
        self.assertNotIn("lia-carvalho-1996", [entry["person"] for entry in late["week"]])

    def test_birth_of_someone_who_died_is_on_this_day(self):
        (result,) = self.mural("2026-06-20")  # Anselmo, born 20 June 1940

        self.assertIn({"kind": "birth", "person": "anselmo-figueira-1940", "years": 86}, result["onThisDay"])
        self.assertNotIn("anselmo-figueira-1940", [entry["person"] for entry in result["week"]])

    def test_deaths_are_remembered_apart(self):
        (result,) = self.mural("2027-01-08")  # Anselmo died on 8 January 2015

        self.assertEqual(result["inMemory"], [{"kind": "death", "person": "anselmo-figueira-1940", "years": 12}])

    def test_wedding_anniversary(self):
        (result,) = self.mural("2029-10-05")  # Bento and Íris, 5 October 2019

        self.assertIn(
            {"kind": "marriage", "people": ["bento-carvalho-1993", "iris-salgueiro-1994"], "years": 10},
            result["onThisDay"],
        )

    def test_born_on_29_february_celebrates_on_the_28th_in_other_years(self):
        leap, other = self.mural("2028-02-29", "2027-02-28")

        self.assertIn(("gabriel-carvalho-2000", 28), [(e["person"], e["years"]) for e in leap["week"] if e["isToday"]])
        self.assertIn(("gabriel-carvalho-2000", 27), [(e["person"], e["years"]) for e in other["week"] if e["isToday"]])

    def test_dates_with_only_the_year_or_approximate_never_appear(self):
        results = self.mural(*[f"2026-{month:02d}-15" for month in range(1, 13)])
        mentioned = {
            entry.get("person")
            for result in results
            for entry in result["week"] + result["onThisDay"] + result["inMemory"]
        }

        self.assertNotIn("teodoro-figueira-1885", mentioned)  # c. 1885
        self.assertNotIn("olga-figueira-1943", mentioned)  # 1943

    def test_day_without_events_shows_a_memory_that_changes_with_the_date(self):
        quiet_days = [f"2026-03-{d:02d}" for d in range(1, 29)]
        results = self.mural(*quiet_days)
        memories = [json.dumps(r["memoryOfTheDay"]) for r in results if not r["onThisDay"]]

        self.assertTrue(memories)
        self.assertTrue(all(memory != "null" for memory in memories))
        self.assertGreater(len(set(memories)), 3)

    def test_new_on_the_site_lists_recent_items_newest_first(self):
        self.data["news"] = [
            {"type": "recipe", "key": "bolo-de-fuba-da-dalva", "date": "2026-11-01"},
            {"type": "person", "key": "theo-carvalho-2021", "date": "2026-09-01"},
            {"type": "person", "key": "lia-carvalho-1996", "date": "2026-11-16"},
        ]

        (result,) = self.mural("2026-11-17")

        self.assertEqual([item["key"] for item in result["news"]], ["lia-carvalho-1996", "bolo-de-fuba-da-dalva"])

    def person(self, identifier):
        return next(p for p in self.data["people"] if p["id"] == identifier)


class SearchTests(JavaScriptTestCase):
    def search(self, **criteria):
        (result,) = self.run_js("search", criteria=[criteria])
        return result

    def test_no_filter_lists_everybody_alphabetically_ignoring_accents(self):
        result = self.search()

        self.assertEqual(len(result), len(self.data["people"]))
        self.assertLess(result.index("alice-loureiro-2016"), result.index("alvaro-figueira-1962"))
        self.assertLess(result.index("alvaro-figueira-1962"), result.index("amelia-castanheira-1941"))

    def test_name_ignores_accents_and_capitals(self):
        self.assertEqual(self.search(text="CECILIA"), ["cecilia-figueira-1964"])
        self.assertEqual(self.search(text="sônia"), ["sonia-cerejeira-1966"])

    def test_nickname_and_several_words(self):
        self.assertEqual(self.search(text="quinzinho"), ["joaquim-carvalho-1938"])
        self.assertEqual(self.search(text="lia carvalho"), ["lia-carvalho-1996"])

    def test_birth_year_range(self):
        result = self.search(**{"from": "1938", "to": "1941"})

        self.assertEqual(
            sorted(result),
            ["amelia-castanheira-1941", "anselmo-figueira-1940", "joaquim-carvalho-1938"],
        )

    def test_single_birth_year(self):
        self.assertEqual(self.search(**{"from": "2021", "to": "2021"}), ["theo-carvalho-2021"])

    def test_birth_place_and_places_lived(self):
        self.assertIn("rui-pinheiro-1965", self.search(born="recife"))
        self.assertNotIn("rui-pinheiro-1965", self.search(born="curitiba"))
        self.assertIn("ines-figueira-1972", self.search(lived="valencia"))

    def test_place_filters_compare_whole_places(self):
        self.assertEqual(self.search(born="sao"), [])
        self.assertEqual(self.search(lived="santo"), [])

    def test_distance_and_generation(self):
        near = self.search(distance="1")
        grandparents = self.search(generation="-2")

        self.assertEqual(
            sorted(near),
            ["davi-amoreira-1995", "helena-figueira-1970", "lia-carvalho-1996", "rui-pinheiro-1965", "tomas-carvalho-1968"],
        )
        self.assertIn("anselmo-figueira-1940", grandparents)
        self.assertIn("gabriel-carvalho-2000", self.search(generation="-1"))

    def test_living_or_deceased(self):
        deceased = self.search(status="deceased")

        self.assertIn("maria-jacaranda-1", deceased)
        self.assertNotIn("lia-carvalho-1996", deceased)
        self.assertNotIn("maria-jacaranda-1", self.search(status="living"))

    def test_occupation_and_tag(self):
        self.assertEqual(self.search(occupation="ferreiro"), ["horacio-figueira-1912", "teodoro-figueira-1885"])
        self.assertIn("ines-figueira-1972", self.search(tag="emigrante"))

    def test_has_photos_interview_or_recipe(self):
        self.assertIn("lia-carvalho-1996", self.search(photos=True))
        self.assertNotIn("davi-amoreira-1995", self.search(photos=True))
        self.assertEqual(self.search(interview=True), ["helena-figueira-1970"])
        self.assertEqual(
            sorted(self.search(recipe=True)),
            ["cecilia-figueira-1964", "dalva-oliveira-1944", "olga-figueira-1943"],
        )

    def test_recipes_are_found_by_title(self):
        (result, empty) = self.run_js("recipes", texts=["bolo FUBA", ""])

        self.assertEqual(result, ["bolo-de-fuba-da-dalva"])
        self.assertEqual(empty, [])


class QuickSearchTests(JavaScriptTestCase):
    """The search in place of the header (static/js/header.js)."""

    def quick(self, *texts, search_href="/pt-br/search/"):
        return self.run_js("quick-search", texts=list(texts), searchHref=search_href)

    def test_names_match_like_the_search_page(self):
        (lia, accents) = self.quick("LIA carvalho", "sônia")

        self.assertEqual(lia["people"], ["lia-carvalho-1996"])
        self.assertEqual(lia["total"], 1)
        self.assertEqual(accents["people"], ["sonia-cerejeira-1966"])

    def test_names_that_start_with_the_text_come_first(self):
        (lia,) = self.quick("lia")

        self.assertEqual(lia["people"][0], "lia-carvalho-1996")
        self.assertIn("amelia-castanheira-1941", lia["people"][1:])

    def test_at_most_eight_people_but_the_count_of_all(self):
        (many,) = self.quick("a")

        self.assertEqual(len(many["people"]), 8)
        self.assertGreater(many["total"], 8)

    def test_nothing_typed_shows_nobody(self):
        (empty,) = self.quick("   ")

        self.assertEqual((empty["people"], empty["total"]), ([], 0))

    def test_nickname_in_quotes_or_else_the_years(self):
        (joaquim, lia) = self.quick("quinzinho", "lia carvalho")
        person = next(p for p in self.data["people"] if p["id"] == "lia-carvalho-1996")

        self.assertEqual(joaquim["details"], ["“Quinzinho”"])
        self.assertEqual(lia["details"], [f"“{person['nickname']}”" if person["nickname"] else person["years"]])

    def test_see_all_opens_the_search_page_with_the_text(self):
        (typed,) = self.quick(" lia & bento ")
        (exported,) = self.quick("lia", search_href="../search/index.html?x=1#top")

        self.assertEqual(typed["seeAll"], "/pt-br/search/?text=lia%20%26%20bento")
        self.assertEqual(exported["seeAll"], "../search/index.html?text=lia")


class ScriptLoaderTests(JavaScriptTestCase):
    """The scripts of the search in place: each fetched once, a failure tried again."""

    def test_reopening_during_a_load_fetches_nothing_twice_and_a_retry_only_the_failed_one(self):
        result = self.run_js("script-loader")

        self.assertEqual(result["afterFirst"], ["data", "common", "search"])
        self.assertEqual(result["added"], ["data", "common", "search", "data"])
        self.assertEqual(
            result["log"],
            [["first", False], ["reopened while loading", False], ["retry", True]],
        )


class SearchPageAddressTests(JavaScriptTestCase):
    def test_text_of_the_address_fills_the_field_only_when_given(self):
        result = self.run_js("initial-text", searches=["?text=lia%20carvalho", "?q=bento", "", "?other=1", "?text="])

        # None: the field keeps what the browser restored after "Back".
        self.assertEqual(result, ["lia carvalho", "bento", None, None, ""])

    def test_search_works_without_kinship(self):
        result = self.run_js("search-without-kinship", criteria={"text": "lia carvalho"})

        self.assertEqual(result, {"found": ["lia-carvalho-1996"], "kinship": False})


class ThemeTests(JavaScriptTestCase):
    def test_same_cycle_as_the_panel(self):
        steps = [["auto", False], ["dark", False], ["light", False], ["auto", True], ["light", True], ["dark", True], ["nonsense", False]]

        self.assertEqual(self.run_js("theme", steps=steps), ["dark", "light", "auto", "light", "dark", "auto", "auto"])

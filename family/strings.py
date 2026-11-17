"""Interface texts used by the scripts that run in the browser.

The pages hand these to their script (as JSON), already translated into the
language of the page. Texts that depend on a number come in two forms,
"one" and "other", chosen by the script.
"""
from django.utils.translation import gettext as _
from django.utils.translation import ngettext


def _plural(singular: str, plural: str) -> dict[str, str]:
    return {"one": ngettext(singular, plural, 1), "other": ngettext(singular, plural, 2)}


def _kinship_strings() -> dict:
    return {
        "side": _("Side of %(name)s"),
        "center": _(
            "%(name)s, siblings, descendants, partners' families and relatives on more than one side"
        ),
        "unlinked": _("No link to %(name)s"),
        "generations": {
            "-4": _("Great-great-grandparents"),
            "-3": _("Great-grandparents"),
            "-2": _("Grandparents"),
            "-1": _("Parents, uncles and aunts"),
            "0": _("Generation of %(name)s"),
            "1": _("Children, nephews and nieces"),
            "2": _("Grandchildren"),
        },
        "generationOther": _("Generation %(number)s"),
        "allSides": _("All sides"),
        "allGenerations": _("All generations"),
    }


def tree_strings() -> dict:
    return {
        **_kinship_strings(),
        "wheelHint": _("Hold Ctrl and turn the mouse wheel to zoom."),
        "touchHint": _("Use two fingers to move and zoom, or open the full screen."),
        "fullScreen": _("Full screen"),
        "exitFullScreen": _("Exit full screen"),
    }


def map_strings() -> dict:
    return {
        **_kinship_strings(),
        "roles": {
            "birth": _("born"),
            "lived": _("lived"),
            "lives": _("lives"),
            "death": _("died"),
            "resting": _("rests"),
        },
        "people": _plural("%(count)s person", "%(count)s people"),
        "noPlaces": _("No place with coordinates matches these filters."),
        "wheelHint": _("Click the map to zoom with the mouse wheel."),
    }


def search_strings() -> dict:
    return {
        **_kinship_strings(),
        "results": _plural("%(count)s person found", "%(count)s people found"),
        "centerShort": _("Close family of %(name)s"),
        "recipes": _("Recipes"),
        "noResults": _("Nobody matches these filters."),
        "recipeBy": _("Recipe of %(name)s"),
        "steps": _plural("%(count)s step away", "%(count)s steps away"),
        "deceased": _("deceased"),
    }


def mural_strings() -> dict:
    return {
        "weekBirthdays": _("Birthdays this week"),
        "today": _("Today"),
        "onThisDay": _("On this day"),
        "inMemory": _("In memory"),
        "newOnSite": _("New on the site"),
        "memoryOfTheDay": _("Memory of the day"),
        "turns": _plural("turns %(years)s", "turns %(years)s"),
        "birthdayToday": _plural(
            "%(name)s turns %(years)s year old today", "%(name)s turns %(years)s years old today"
        ),
        "bornAgo": _plural(
            "%(years)s year ago, %(name)s was born", "%(years)s years ago, %(name)s was born"
        ),
        "marriageAgo": _plural(
            "%(years)s year ago, %(a)s and %(b)s got married",
            "%(years)s years ago, %(a)s and %(b)s got married",
        ),
        "unionAgo": _plural(
            "%(years)s year ago, %(a)s and %(b)s started their life together",
            "%(years)s years ago, %(a)s and %(b)s started their life together",
        ),
        "datingAgo": _plural(
            "%(years)s year ago, %(a)s and %(b)s started dating",
            "%(years)s years ago, %(a)s and %(b)s started dating",
        ),
        "photoAgo": _plural("Photo from %(years)s year ago", "Photo from %(years)s years ago"),
        "deathAgo": _plural(
            "%(years)s year ago, %(name)s passed away", "%(years)s years ago, %(name)s passed away"
        ),
        "newPerson": _("New page: %(name)s"),
        "newPhoto": _("New photo"),
        "newRecipe": _("New recipe: %(title)s"),
        "andMore": _("and %(count)s more"),
        "recipeBy": _("Recipe of %(name)s"),
        "nothing": _("Nothing to show yet."),
    }

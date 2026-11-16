"""Finds links that point nowhere in the texts of the family.

Used by the admin (a warning after saving) and by the export (which stops
instead of publishing a site with broken links).
"""
from django.utils.translation import gettext as _

from .markup import LinkTargets, render_text
from .models import TEXT_SECTIONS, Person, Recipe, Union


def person_problems(person: Person, targets: LinkTargets) -> list[str]:
    """Problems in the texts of one person, each starting with the section title."""
    problems = []
    for field_name, title in TEXT_SECTIONS:
        result = render_text(getattr(person, field_name), targets, video_id=person.youtube_id)
        problems += [f"{title}: {problem}" for problem in result.problems]
    return problems


def union_problems(union: Union, targets: LinkTargets) -> list[str]:
    """Problems in the story of a couple."""
    return render_text(union.story, targets).problems


def all_text_problems() -> list[str]:
    """Every problem in every text, each saying where it is."""
    targets = LinkTargets.from_database()
    problems = []
    for person in Person.objects.all():
        problems += [f"{person.full_name}, {problem}" for problem in person_problems(person, targets)]
    for union in Union.objects.select_related("partner1", "partner2").exclude(story=""):
        story = _("story of the couple")
        problems += [f"{union}, {story}: {problem}" for problem in union_problems(union, targets)]
    for recipe in Recipe.objects.exclude(text=""):
        result = render_text(recipe.text, targets)
        problems += [f"{recipe.title}: {problem}" for problem in result.problems]
    return problems

"""Turns the texts typed in the admin into the HTML shown on the pages.

The texts are written in Markdown, with two additions:

    [[ramon-garcia-1962]]              link to a person, showing the full name
    [[ramon-garcia-1962|o tio Moncho]] link to a person, showing the chosen text
    [[lugar:valencia]]                 the name of a place
    [[receita:feijoada-da-vo]]         the title of a recipe
    [04:12]                            link to that minute of the interview

A link to something that does not exist is never ignored: it is reported as a
problem, shown in the admin and blocking the export.
"""
import xml.etree.ElementTree as etree
from dataclasses import dataclass, field

import markdown
from django.urls import reverse
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext as _
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

from .youtube import watch_url

_WIKILINK = r"\[\[([^\[\]|]+)(?:\|([^\[\]]+))?\]\]"
# [mm:ss] or [h:mm:ss], but not the text of a normal link: [04:12](https://...)
_TIMESTAMP = r"\[(\d{1,3}):([0-5]\d)(?::([0-5]\d))?\](?!\()"

_PLACE_PREFIXES = {"lugar", "place"}
_RECIPE_PREFIXES = {"receita", "receta", "recipe"}

# Run after code spans and escapes, before Markdown's own links.
_PRIORITY = 175


@dataclass
class LinkTargets:
    """Everything a [[link]] may point to: {identifier: name shown}."""

    people: dict[str, str] = field(default_factory=dict)
    places: dict[str, str] = field(default_factory=dict)
    recipes: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_database(cls) -> "LinkTargets":
        from .models import Person, Place, Recipe

        return cls(
            people={person.identifier: person.full_name for person in Person.objects.all()},
            places=dict(Place.objects.values_list("slug", "name")),
            recipes=dict(Recipe.objects.values_list("slug", "title")),
        )


@dataclass
class Rendered:
    html: SafeString
    problems: list[str]


def _broken(original: str, problem: str) -> etree.Element:
    element = etree.Element("span")
    element.set("class", "broken-link")
    element.set("title", problem)
    element.text = original
    return element


class _WikiLinkProcessor(InlineProcessor):
    def __init__(self, pattern, md, targets: LinkTargets, problems: list[str]):
        super().__init__(pattern, md)
        self.targets = targets
        self.problems = problems

    def handleMatch(self, match, data):
        original = match.group(0)
        target = match.group(1).strip()
        label = (match.group(2) or "").strip()
        prefix, separator, rest = target.partition(":")
        prefix = prefix.strip().lower()

        if separator and prefix in _PLACE_PREFIXES:
            element = self._named(rest, label, self.targets.places, "place-name")
            problem = _("%(link)s: there is no place with this identifier.")
        elif separator and prefix in _RECIPE_PREFIXES:
            element = self._named(rest, label, self.targets.recipes, "recipe-name")
            problem = _("%(link)s: there is no recipe with this identifier.")
        else:
            element = self._person(target, label)
            problem = _("%(link)s: there is no person with this identifier.")

        if element is None:
            problem = problem % {"link": original}
            self.problems.append(problem)
            element = _broken(original, problem)
        return element, match.start(0), match.end(0)

    def _person(self, identifier: str, label: str) -> etree.Element | None:
        if identifier not in self.targets.people:
            return None
        element = etree.Element("a")
        element.set("class", "person-link")
        element.set("href", reverse("family:person_detail", args=[identifier]))
        element.text = label or self.targets.people[identifier]
        return element

    def _named(self, slug: str, label: str, names: dict[str, str], css_class: str):
        slug = slug.strip()
        if slug not in names:
            return None
        element = etree.Element("span")
        element.set("class", css_class)
        element.text = label or names[slug]
        return element


class _TimestampProcessor(InlineProcessor):
    def __init__(self, pattern, md, video_id: str | None, problems: list[str]):
        super().__init__(pattern, md)
        self.video_id = video_id
        self.problems = problems

    def handleMatch(self, match, data):
        original = match.group(0)
        first, second, third = match.group(1), match.group(2), match.group(3)
        if third is None:
            seconds = int(first) * 60 + int(second)
        else:
            seconds = int(first) * 3600 + int(second) * 60 + int(third)

        if not self.video_id:
            self.problems.append(
                _("%(time)s: there is no interview to link this minute to.") % {"time": original}
            )
            element = etree.Element("span")
            element.set("class", "broken-link")
            element.text = original
        else:
            element = etree.Element("a")
            element.set("class", "timestamp")
            element.set("data-seconds", str(seconds))
            element.set("href", watch_url(self.video_id, start=seconds))
            element.text = original[1:-1]
        return element, match.start(0), match.end(0)


class _RaizesExtension(Extension):
    def __init__(self, targets: LinkTargets, video_id: str | None, problems: list[str]):
        super().__init__()
        self.targets = targets
        self.video_id = video_id
        self.problems = problems

    def extendMarkdown(self, md):
        # HTML typed in a text is shown as text instead of being interpreted:
        # a stray "<" cannot break the page.
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")
        md.inlinePatterns.register(
            _WikiLinkProcessor(_WIKILINK, md, self.targets, self.problems),
            "raizes_wikilink",
            _PRIORITY,
        )
        md.inlinePatterns.register(
            _TimestampProcessor(_TIMESTAMP, md, self.video_id, self.problems),
            "raizes_timestamp",
            _PRIORITY - 1,
        )


def render_text(text: str, targets: LinkTargets, video_id: str | None = None) -> Rendered:
    """Convert a text to HTML and report every link that points nowhere.

    `video_id` is the code of the person's interview; without it, [mm:ss]
    cannot become a link and is reported as a problem.
    """
    if not (text or "").strip():
        return Rendered(mark_safe(""), [])
    problems: list[str] = []
    converter = markdown.Markdown(
        extensions=["nl2br", "sane_lists", _RaizesExtension(targets, video_id, problems)],
        output_format="html",
    )
    return Rendered(mark_safe(converter.convert(text)), problems)

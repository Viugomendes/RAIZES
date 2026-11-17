"""The family's data as the browser sees it (the file data/family.js).

The search, the mural and the maps run in the browser, without a server, so they read everything from this file. Only
what the pages already show goes into it: never notes for the owner, never
the original photos.

It is a JavaScript file (not JSON) so that it also works when the exported
site is opened straight from the disk, where browsers refuse to "fetch" files.
"""
import datetime
import json
import re
from pathlib import Path

from django.conf import settings

from access.config import central_person_identifier

from .dates import PartialDate
from .graph import load_family_graph
from .images import AVATAR, LARGE, THUMB, variant_url
from .models import TEXT_SECTIONS, Person, Photo, Place, Recipe, Union

NEWS_DAYS = 30  # "new on the site" shows what was first published in these days
_QUOTE_LINE = re.compile(r"^\s*>\s?(.*)$")


def _date(value: PartialDate | None) -> list[int] | None:
    """[year] or [year, month, day]; None when unknown."""
    if value is None:
        return None
    if value.is_complete:
        return [value.year, value.month, value.day]
    return [value.year]


def _url(name: str, width: int) -> str:
    """Address of a photo copy, relative to the root of the site."""
    return variant_url(name, width).lstrip("/")


def _phrases(person: Person) -> list[str]:
    """Quotes ("> ...") written in the texts of a person."""
    found = []
    for key, _title in TEXT_SECTIONS:
        if key in settings.RAIZES_HIDDEN_SECTIONS:
            continue
        lines = []
        for line in getattr(person, key).splitlines() + [""]:
            match = _QUOTE_LINE.match(line)
            if match:
                lines.append(match[1].strip())
            elif lines:
                text = " ".join(part for part in lines if part)
                if text:
                    found.append(text)
                lines = []
    return found


# Items present in the first publication: they are the starting point, not news.
INITIAL = "initial"


def read_history() -> dict:
    """{"first_seen": {"person:lia-carvalho-1996": "2026-11-17" or "initial"},
    "publications": ["2026-11-17", ...]}"""
    path = Path(settings.RAIZES_HISTORY_FILE)
    try:
        stored = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except (ValueError, OSError):
        stored = {}
    if "first_seen" not in stored:  # older format: a plain {key: date}
        stored = {"first_seen": stored, "publications": sorted(set(stored.values()))[:1]}
    stored.setdefault("publications", [])
    return stored


def item_keys() -> list[str]:
    """Every item that can be "new on the site"."""
    keys = [f"person:{i}" for i in Person.objects.values_list("identifier", flat=True)]
    keys += [f"photo:{i}" for i in Photo.objects.values_list("pk", flat=True)]
    keys += [f"recipe:{i}" for i in Recipe.objects.values_list("slug", flat=True)]
    return keys


def update_history(today: datetime.date | None = None) -> None:
    """Record a publication: items never published before get today's date.

    In the very first publication everything is the starting point, so
    nothing is marked as new.
    """
    history = read_history()
    stamp = (today or datetime.date.today()).isoformat()
    first = not history["publications"]
    for key in item_keys():
        history["first_seen"].setdefault(key, INITIAL if first else stamp)
    history["publications"].append(stamp)
    path = Path(settings.RAIZES_HISTORY_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=1, sort_keys=True), encoding="utf-8")

def build_site_data(today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()
    graph = load_family_graph()
    people = {person.identifier: person for person in Person.objects.prefetch_related("lived_in")}
    wanted_central = central_person_identifier()
    central = wanted_central if wanted_central in people else None

    photo_counts: dict[str, int] = {}
    photos = []
    for photo in Photo.objects.prefetch_related("people").select_related("place"):
        tagged = [person.identifier for person in photo.people.all()]
        for identifier in tagged:
            photo_counts[identifier] = photo_counts.get(identifier, 0) + 1
        photos.append(
            {
                "id": photo.pk,
                "thumb": _url(photo.image.name, THUMB),
                "large": _url(photo.image.name, LARGE),
                "date": _date(photo.taken),
                "caption": photo.caption,
                "people": tagged,
                "unknown": photo.has_unidentified_people,
                "place": photo.place.slug if photo.place else None,
            }
        )

    recipes = []
    recipe_counts: dict[str, int] = {}
    for recipe in Recipe.objects.select_related("author"):
        author = recipe.author.identifier if recipe.author else None
        if author:
            recipe_counts[author] = recipe_counts.get(author, 0) + 1
        recipes.append(
            {
                "slug": recipe.slug,
                "title": recipe.title,
                "author": author,
                "thumb": _url(recipe.photo.name, THUMB) if recipe.photo else "",
            }
        )

    people_data = []
    phrases = []
    for identifier in graph.people:  # ordered by birth, like the kinship rules
        person = people[identifier]
        people_data.append(
            {
                "id": identifier,
                "name": person.full_name,
                "given": person.given_name,
                "surname": person.surname,
                "nickname": person.nickname,
                "otherNames": person.other_names,
                "initials": person.initials,
                "years": person.years_display,
                "birth": _date(person.birth),
                "birthApprox": person.birth_date_approximate,
                "death": _date(person.death),
                "deathApprox": person.death_date_approximate,
                "deceased": person.is_deceased,
                "occupation": person.occupation,
                "tags": person.tag_list,
                "birthPlace": person.birth_place.slug if person.birth_place_id else None,
                "deathPlace": person.death_place.slug if person.death_place_id else None,
                "restingPlace": person.resting_place.slug if person.resting_place_id else None,
                "livesIn": person.lives_in.slug if person.lives_in_id and not person.is_deceased else None,
                "livedIn": [place.slug for place in person.lived_in.all()],
                "avatar": _url(person.photo.name, AVATAR) if person.photo else "",
                "interview": bool(person.youtube_id),
                "photos": photo_counts.get(identifier, 0),
                "recipes": recipe_counts.get(identifier, 0),
            }
        )
        phrases += [{"text": text, "person": identifier} for text in _phrases(person)]

    stored_unions = {union.pk: union for union in Union.objects.all()}
    unions = []
    for record in graph.unions:
        union = stored_unions[record.id]
        unions.append(
            {
                "id": record.id,
                "partners": list(record.partners),
                "kind": union.kind,
                "start": _date(union.start),
                "end": _date(union.end),
                "ended": union.is_ended,
                "children": [list(child) for child in record.children],
            }
        )

    places = {
        place.slug: {"name": place.name, "lat": place.latitude, "lon": place.longitude}
        for place in Place.objects.all()
    }

    history = read_history()
    oldest = (today - datetime.timedelta(days=NEWS_DAYS)).isoformat()
    news = []
    for key in item_keys():
        # Not published yet: new, unless nothing was ever published (then the
        # next publication is the starting point).
        unpublished = today.isoformat() if history["publications"] else INITIAL
        first = history["first_seen"].get(key, unpublished)
        if first != INITIAL and first >= oldest:
            kind, _colon, ident = key.partition(":")
            news.append({"type": kind, "key": ident, "date": first})
    news.sort(key=lambda item: (item["date"], item["type"], item["key"]), reverse=True)

    return {
        "central": central,
        "people": people_data,
        "unions": unions,
        "places": places,
        "photos": photos,
        "recipes": recipes,
        "phrases": phrases,
        "news": news,
        "newsDays": NEWS_DAYS,
    }


def site_data_script(today: datetime.date | None = None) -> str:
    payload = json.dumps(build_site_data(today), ensure_ascii=False, separators=(",", ":"))
    # "</" cannot end a <script> early, and the file stays valid JavaScript.
    payload = payload.replace("</", "<\\/").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return f"window.RAIZES_DATA = {payload};\n"

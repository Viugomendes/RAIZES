"""Loads the invented family of demo/family.toml into the database.

The invented family is used for tests, examples and screenshots, so that the
real family's data is never needed to work on the site.
"""
import colorsys
import hashlib
import io
import tomllib
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from .models import ChildLink, Person, Photo, Place, Recipe, Union

DEMO_FILE = Path(settings.BASE_DIR) / "demo" / "family.toml"

# Fields of a person that point to a place (written as the place's slug).
PLACE_FIELDS = ("birth_place", "death_place", "resting_place", "lives_in")

# Keys of a union that list children, and the kind of link each one means.
CHILDREN_KEYS = {
    "children": ChildLink.Kind.BIOLOGICAL,
    "adoptive_children": ChildLink.Kind.ADOPTIVE,
    "foster_children": ChildLink.Kind.FOSTER,
}


def read_demo_file(path: Path = DEMO_FILE) -> dict:
    with open(path, "rb") as file:
        return tomllib.load(file)


def _save_valid(record, label: str):
    """Validate a record exactly like the admin does, then save it."""
    try:
        record.full_clean()
    except ValidationError as error:
        raise ValueError(f"{label}: {error}") from error
    record.save()
    return record


def _delete_family_data() -> None:
    for person in Person.objects.exclude(photo=""):
        person.photo.delete(save=False)
    Union.objects.all().delete()  # also deletes the child links
    Recipe.objects.all().delete()
    Photo.objects.all().delete()
    Person.objects.all().delete()
    Place.objects.all().delete()


def draw_portrait(person: Person) -> bytes:
    """A placeholder picture: the person's initials on a coloured background."""
    digest = hashlib.sha256(person.identifier.encode()).digest()
    red, green, blue = colorsys.hls_to_rgb(digest[0] / 255, 0.72, 0.45)
    background = (int(red * 255), int(green * 255), int(blue * 255))

    image = Image.new("RGB", (400, 400), background)
    draw = ImageDraw.Draw(image)
    draw.text(
        (200, 200),
        person.initials,
        fill=(255, 255, 255),
        font=ImageFont.load_default(size=170),
        anchor="mm",
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@transaction.atomic
def load_demo_family(path: Path = DEMO_FILE, with_portraits: bool = True) -> dict[str, int]:
    """Replace everything in the database with the invented family.

    Returns how many records of each kind were created.
    """
    data = read_demo_file(path)
    _delete_family_data()

    places = {}
    for entry in data.get("places", []):
        places[entry["slug"]] = _save_valid(Place(**entry), f"place {entry['slug']}")

    people = {}
    for entry in data.get("people", []):
        entry = dict(entry)
        identifier = entry["identifier"]
        lived_in = entry.pop("lived_in", [])
        wants_portrait = entry.pop("portrait", False)
        for field in PLACE_FIELDS:
            if field in entry:
                entry[field] = places[entry[field]]
        person = _save_valid(Person(**entry), f"person {identifier}")
        person.lived_in.set([places[slug] for slug in lived_in])
        if wants_portrait and with_portraits:
            person.photo.save(f"{identifier}.png", ContentFile(draw_portrait(person)), save=True)
        people[identifier] = person

    unions = 0
    for entry in data.get("unions", []):
        entry = dict(entry)
        partner_ids = entry.pop("partners")
        children = {kind: entry.pop(key, []) for key, kind in CHILDREN_KEYS.items()}
        label = "union " + " + ".join(partner_ids)
        partners = [people[identifier] for identifier in partner_ids]
        union = _save_valid(
            Union(
                partner1=partners[0],
                partner2=partners[1] if len(partners) > 1 else None,
                **entry,
            ),
            label,
        )
        for kind, child_ids in children.items():
            for child_id in child_ids:
                _save_valid(
                    ChildLink(union=union, child=people[child_id], kind=kind),
                    f"{label}, child {child_id}",
                )
        unions += 1

    recipes = 0
    for entry in data.get("recipes", []):
        entry = dict(entry)
        author = entry.pop("author", None)
        _save_valid(
            Recipe(author=people[author] if author else None, **entry),
            f"recipe {entry['slug']}",
        )
        recipes += 1

    return {
        "places": len(places),
        "people": len(people),
        "unions": unions,
        "recipes": recipes,
    }

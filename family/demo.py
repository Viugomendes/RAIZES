"""Loads the invented family of demo/family.toml into the database.

The invented family is used for tests, examples and screenshots, so that the
real family's data is never needed to work on the site.
"""
import colorsys
import hashlib
import io
import math
import struct
import tomllib
import wave
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

from .models import ChildLink, Clip, Person, Photo, Place, Recipe, Union

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
    """Erase every record and every media file of the database in use."""
    for person in Person.objects.exclude(photo=""):
        person.photo.delete(save=False)
    for photo in Photo.objects.all():
        photo.image.delete(save=False)
    for clip in Clip.objects.all():
        clip.file.delete(save=False)
    for recipe in Recipe.objects.exclude(photo=""):
        recipe.photo.delete(save=False)
    Union.objects.all().delete()  # also deletes the child links
    Recipe.objects.all().delete()
    Photo.objects.all().delete()
    Clip.objects.all().delete()
    Person.objects.all().delete()
    Place.objects.all().delete()


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _colour(seed: str, lightness: float = 0.72, saturation: float = 0.45) -> tuple[int, int, int]:
    digest = hashlib.sha256(seed.encode()).digest()
    red, green, blue = colorsys.hls_to_rgb(digest[0] / 255, lightness, saturation)
    return (int(red * 255), int(green * 255), int(blue * 255))


def draw_portrait(person: Person) -> bytes:
    """A placeholder picture: the person's initials on a coloured background."""
    image = Image.new("RGB", (400, 400), _colour(person.identifier))
    draw = ImageDraw.Draw(image)
    draw.text((200, 200), person.initials, fill=(255, 255, 255), font=ImageFont.load_default(size=170), anchor="mm")
    return _png(image)


def draw_scene(seed: str, caption: str) -> bytes:
    """A placeholder "photo": sky, hills, some round figures and the caption."""
    width, height = 1200, 800
    image = Image.new("RGB", (width, height), _colour(seed + "sky", 0.82, 0.5))
    draw = ImageDraw.Draw(image)
    draw.ellipse((-200, 480, 900, 1100), fill=_colour(seed + "hill", 0.45, 0.35))
    draw.ellipse((500, 520, 1500, 1200), fill=_colour(seed + "hill2", 0.38, 0.3))
    digest = hashlib.sha256(seed.encode()).digest()
    for index in range(2 + digest[1] % 4):
        x = 260 + index * 180
        figure = _colour(f"{seed}{index}", 0.35, 0.4)
        draw.ellipse((x - 40, 330, x + 40, 410), fill=figure)
        draw.rounded_rectangle((x - 55, 415, x + 55, 620), radius=40, fill=figure)
    draw.rectangle((0, height - 110, width, height), fill=(255, 255, 255))
    draw.text((40, height - 55), caption, fill=(40, 40, 40), font=ImageFont.load_default(size=40), anchor="lm")
    draw.text((width - 40, 40), "Foto inventada", fill=(255, 255, 255), font=ImageFont.load_default(size=34), anchor="ra")
    return _png(image)


def make_tone(seconds: float = 2.0) -> bytes:
    """A short invented recording: a few soft notes (WAV)."""
    rate = 22050
    notes = [392.0, 440.0, 523.25, 440.0]
    frames = bytearray()
    total = int(rate * seconds)
    for index in range(total):
        note = notes[int(index / total * len(notes)) % len(notes)]
        envelope = min(1.0, index / 400, (total - index) / 400)
        value = int(9000 * envelope * math.sin(2 * math.pi * note * index / rate))
        frames += struct.pack("<h", value)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(bytes(frames))
    return buffer.getvalue()


@transaction.atomic
def load_demo_family(path: Path = DEMO_FILE) -> dict[str, int]:
    """Replace everything in the database with the invented family.

    The pictures and the recording are drawn on the spot, into the media
    folder in use. Returns how many records of each kind were created.
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
        if wants_portrait:
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
            Union(partner1=partners[0], partner2=partners[1] if len(partners) > 1 else None, **entry),
            label,
        )
        for kind, child_ids in children.items():
            for child_id in child_ids:
                _save_valid(ChildLink(union=union, child=people[child_id], kind=kind), f"{label}, child {child_id}")
        unions += 1

    photos = 0
    for entry in data.get("photos", []):
        entry = dict(entry)
        name = entry.pop("name")
        tagged = entry.pop("people", [])
        if "place" in entry:
            entry["place"] = places[entry["place"]]
        photo = Photo(**entry)
        photo.image.save(f"{name}.png", ContentFile(draw_scene(name, entry.get("caption", ""))), save=False)
        _save_valid(photo, f"photo {name}")
        photo.people.set([people[identifier] for identifier in tagged])
        photos += 1

    clips = 0
    for entry in data.get("clips", []):
        entry = dict(entry)
        name = entry.pop("name")
        tagged = entry.pop("people", [])
        clip = Clip(**entry)
        clip.file.save(f"{name}.wav", ContentFile(make_tone()), save=False)
        _save_valid(clip, f"clip {name}")
        clip.people.set([people[identifier] for identifier in tagged])
        clips += 1

    recipes = 0
    for entry in data.get("recipes", []):
        entry = dict(entry)
        author = entry.pop("author", None)
        recipe = Recipe(author=people[author] if author else None, **entry)
        recipe.photo.save(f"{entry['slug']}.png", ContentFile(draw_scene(entry["slug"], entry["title"])), save=False)
        _save_valid(recipe, f"recipe {entry['slug']}")
        recipes += 1

    return {
        "places": len(places),
        "people": len(people),
        "unions": unions,
        "photos": photos,
        "clips": clips,
        "recipes": recipes,
    }
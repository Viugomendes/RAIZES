"""The identifier of a person: `name-surname-year`.

It is the address of the person's page and the name used in [[links]], so it
never changes after it is created.
"""
import re
import unicodedata
from collections.abc import Callable

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

# Small words that are part of a surname but say little: "da Silva" -> "silva".
_PARTICLES = {"da", "de", "do", "das", "dos", "del", "la", "las", "los", "e", "y", "di", "van", "von"}


def is_valid_identifier(identifier: str) -> bool:
    """Lowercase letters and digits, in groups separated by single hyphens."""
    return bool(_IDENTIFIER.match(identifier or ""))


def _plain_words(text: str) -> list[str]:
    """Lowercase words without accents: "García Ortega" -> ["garcia", "ortega"]."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    return re.findall(r"[a-z0-9]+", ascii_text)


def suggest_identifier(
    given_name: str,
    surname: str,
    year: int | None,
    is_taken: Callable[[str], bool],
) -> str:
    """Build a free identifier from the first name, first surname and birth year.

    With an unknown year a number takes its place: `maria-silva-1`. When the
    identifier already exists, a number is added at the end:
    `ramon-garcia-1962-2`.
    """
    parts = _plain_words(given_name)[:1]
    surname_words = _plain_words(surname)
    meaningful = [word for word in surname_words if word not in _PARTICLES]
    parts += (meaningful or surname_words)[:1]
    base = "-".join(parts) or "person"

    if year is None:
        number = 1
        while is_taken(f"{base}-{number}"):
            number += 1
        return f"{base}-{number}"

    candidate = f"{base}-{year}"
    number = 2
    while is_taken(candidate):
        candidate = f"{base}-{year}-{number}"
        number += 1
    return candidate

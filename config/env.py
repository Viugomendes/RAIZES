"""Reads the local `.env` file.

`.env` holds the settings that are different on each computer and the ones
that must stay secret. Git ignores it, so nothing written there is published.
The format is one `NAME=value` per line; lines starting with `#` are comments.
"""
import os
from pathlib import Path

from django.core.management.utils import get_random_secret_key


def read_env_file(path: Path) -> dict[str, str]:
    """Return the `NAME=value` pairs found in the file (empty if it is missing)."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[name.strip()] = value
    return values


def load_env_file(path: Path) -> None:
    """Copy the file's values into the environment.

    A variable that is already set in the real environment wins, so a value
    typed in the terminal overrides the file.
    """
    for name, value in read_env_file(path).items():
        os.environ.setdefault(name, value)


def get_or_create_secret_key(path: Path, name: str = "RAIZES_SECRET_KEY") -> str:
    """Return Django's secret key, creating it in `.env` on the first run.

    The key is never written in the code: each computer generates its own.
    """
    key = os.environ.get(name)
    if key:
        return key
    key = get_random_secret_key()
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    # The key may contain "#" or "$", so it is stored between quotes.
    path.write_text(f"{existing}{name}='{key}'\n", encoding="utf-8")
    os.environ[name] = key
    return key

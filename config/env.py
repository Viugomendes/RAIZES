"""Reads the local `.env` file.

`.env` holds the settings that are different on each computer and the ones
that must stay secret. Git ignores it, so nothing written there is published.
The format is one `NAME=value` per line; lines starting with `#` are comments.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
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


def owner_only(path: Path, mode: int = 0o600) -> None:
    """Only the owner reads it (0o600; 0o700 for a folder): it holds secrets.

    On Windows only the read-only flag exists, and these modes leave it off.
    """
    os.chmod(path, mode)


def parse_list(text: str) -> list[str]:
    """ "tastes, Legacy" -> ["tastes", "legacy"]."""
    return [part.strip().lower() for part in (text or "").split(",") if part.strip()]


def parse_bool(text: str | None, name: str) -> bool:
    """ "true"/"1"/"yes"/"on" or empty -> True; "false"/"0"/"no"/"off" -> False.

    Anything else is an error: a typo must never switch a protection off.
    """
    value = (text or "").strip().lower()
    if value in ("", "true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    raise ImproperlyConfigured(f"{name} must be true or false (check the .env file), not {text!r}.")


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
    owner_only(path)
    os.environ[name] = key
    return key


def set_env_values(path: Path, values: dict[str, str]) -> None:
    """Write `NAME=value` lines into `.env`, replacing a name already there.

    Every other line (comments, the secret key) is kept as it is.
    """
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    for name, value in values.items():
        if "\n" in value or "\r" in value:
            raise ValueError(f"{name} cannot have a line break.")
        if value != value.strip() or "#" in value or value[:1] in "\"'":
            quote = '"' if "'" in value else "'"
            value = f"{quote}{value}{quote}"
        lines = [existing for existing in lines if existing.partition("=")[0].strip() != name]
        lines.append(f"{name}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    owner_only(path)

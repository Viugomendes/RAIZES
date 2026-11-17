"""Smaller copies of the photos, the only ones that reach the site.

The original files stay in the media folder on the owner's computer. The
site uses JPEG copies of a few fixed widths, made with Pillow:

- turned upright when the camera stored the photo sideways;
- without the hidden data of the file (camera model, date, GPS position);
- never larger than the original.

Copies are kept in a cache folder, so each one is made only once, and are
made again when the original changes.
"""
import hashlib
from pathlib import Path, PurePosixPath

from django.conf import settings
from PIL import Image, ImageOps, UnidentifiedImageError

AVATAR = 320  # main photo of a person
THUMB = 480  # gallery thumbnails, search results
LARGE = 1600  # a photo opened on its own
WIDTHS = (AVATAR, THUMB, LARGE)

URL_PREFIX = "v"  # /media/v/<width>/<original name>.jpg
QUALITY = 82


class VariantError(Exception):
    """The copy cannot be made (unknown width, missing file, not an image...)."""


def variant_url(name: str, width: int) -> str:
    """Address of the copy of a media file, or "" when there is no file."""
    if not name:
        return ""
    return f"{settings.MEDIA_URL}{URL_PREFIX}/{width}/{name}.jpg"


def _original(name: str) -> Path:
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise VariantError(f"invalid file name: {name!r}")
    root = Path(settings.MEDIA_ROOT).resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise VariantError(f"no such file: {name!r}")
    return path


def make_variant(name: str, width: int) -> Path:
    """Make (or reuse) the copy of `name` at `width` and return its path."""
    if width not in WIDTHS:
        raise VariantError(f"unknown width: {width}")
    original = _original(name)
    stat = original.stat()
    # The key changes when the original changes, so a stale copy is never used.
    key = hashlib.sha256(f"{name}|{stat.st_size}|{stat.st_mtime_ns}".encode()).hexdigest()[:20]
    cached = Path(settings.RAIZES_CACHE_DIR) / f"{width}" / f"{key}.jpg"
    if cached.is_file():
        return cached

    try:
        with Image.open(original) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGBA")
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image.thumbnail((width, width), Image.Resampling.LANCZOS)
            cached.parent.mkdir(parents=True, exist_ok=True)
            temporary = cached.with_suffix(".tmp")
            # No "exif" argument: the copy carries none of the original's data.
            image.save(temporary, format="JPEG", quality=QUALITY, optimize=True, progressive=True)
            temporary.replace(cached)
    except (UnidentifiedImageError, OSError) as error:
        raise VariantError(f"not an image: {name!r}") from error
    return cached


def parse_variant_path(path: str) -> tuple[int, str] | None:
    """Read "<width>/<name>.jpg" (the end of a copy's address)."""
    width, _slash, rest = path.partition("/")
    if not width.isdigit() or not rest.endswith(".jpg"):
        return None
    return int(width), rest[: -len(".jpg")]

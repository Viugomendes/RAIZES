"""Exports the site as static files (HTML, CSS, JavaScript and photos).

The result opens in a browser without Django running, and is what will be
sent to the hosting. Until version 1.0 this is the only way the family sees
the site: the admin panel never leaves the owner's computer.

The pages are rendered by django-distill, which asks Django for each page
exactly as a browser would and saves the answer in a file.
"""
import posixpath
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from django.conf import settings
from django.contrib.staticfiles import finders
from django.utils import translation
from django.utils.translation import gettext as _
from django_distill.errors import DistillError
from django_distill.renderer import DistillRenderer, render_pattern
from django_distill.request import get_static_filepath, get_uri_values
from django_distill.utils import get_langs

from access.middleware import exporting

from .models import Clip, Person, Photo, Recipe
from .images import URL_PREFIX, VariantError, make_variant, parse_variant_path
from .site_data import update_history
from .textcheck import all_text_problems

# A file left in the exported folder. A folder is only ever erased by the
# export when this file is in it, so no other folder can be wiped by mistake.
MARKER = ".raizes-export"

_LINK = re.compile(r'(?P<attribute>href|src|data-root)="(?P<url>[^"]*)"')
# References to media files, in pages and in data/family.js (with or without the first "/").
_MEDIA_REFERENCE = re.compile(r"/?media/(?P<path>(?:v/\d+/|clips/)[^\"'\s?#<>]+)")
_EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|//|#)", re.IGNORECASE)


class ExportError(Exception):
    """The export could not be done. `problems` lists what must be fixed."""

    def __init__(self, message: str, problems: list[str] | None = None):
        super().__init__(message)
        self.problems = problems or []


@dataclass
class ExportReport:
    output_dir: Path
    pages: int
    files: int
    size: int  # in bytes


def export_site(output_dir: Path | str | None = None) -> ExportReport:
    """Write the whole site into `output_dir` (by default, the dist/ folder)."""
    output_dir = Path(output_dir or settings.RAIZES_EXPORT_DIR).resolve()

    # Nothing is written while a text has a link that points nowhere.
    problems = all_text_problems()
    if problems:
        raise ExportError(
            _("The site was not exported: some texts have links that point nowhere."),
            problems,
        )

    _prepare_folder(output_dir)
    pages = _render_pages(output_dir)
    _copy_static_files(output_dir / settings.STATIC_URL.strip("/"))
    _write_media(output_dir)
    _write_front_door(output_dir)
    (output_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    _make_links_relative(output_dir)

    dead_links = find_dead_links(output_dir)
    if dead_links:
        raise ExportError(_("The exported site has links to files that do not exist."), dead_links)

    # Only an export to the folder that is published (dist/) counts as a
    # publication for "new on the site"; a test export elsewhere does not.
    if output_dir == Path(settings.RAIZES_EXPORT_DIR).resolve():
        update_history()

    files = [path for path in output_dir.rglob("*") if path.is_file()]
    return ExportReport(
        output_dir=output_dir,
        pages=pages,
        files=len(files),
        size=sum(path.stat().st_size for path in files),
    )


def _prepare_folder(output_dir: Path) -> None:
    """Empty the folder of a previous export, or create it."""
    if output_dir.exists():
        if not output_dir.is_dir():
            raise ExportError(_("%(folder)s is not a folder.") % {"folder": output_dir})
        contents = list(output_dir.iterdir())
        if contents and not (output_dir / MARKER).is_file():
            raise ExportError(
                _(
                    "The folder %(folder)s has files that were not created by the "
                    "export, so it was left untouched. Choose an empty folder."
                )
                % {"folder": output_dir}
            )
        for item in contents:
            if item.is_dir() and not item.is_symlink():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        output_dir.mkdir(parents=True)
    (output_dir / MARKER).write_text(
        "This folder was created by `python manage.py export_site`.\n"
        "Its contents are erased and written again at every export.\n",
        encoding="utf-8",
    )


def _pages_to_render(renderer):
    """(pattern, parameters) of every page to write.

    A page with a parameter (one per person, one per recipe) whose list is
    empty is skipped: django-distill would otherwise try to build its address
    without the parameter, and a family without recipes could not export.
    """
    for pattern in renderer.urls_to_render:
        values = get_uri_values(pattern.distill_func, pattern.name)
        if pattern.pattern.converters and list(values) == [None]:
            continue
        for parameters in values:
            if not parameters:
                parameters = ()
            elif isinstance(parameters, str):
                parameters = (parameters,)
            yield pattern, parameters


def _render_pages(output_dir: Path) -> int:
    """Render every page marked with `distill_path=True`, in every language."""
    language_before = translation.get_language()
    written: set[Path] = set()
    try:
        # The pages are asked from Django itself: the view password does not apply.
        with exporting(), DistillRenderer() as renderer:
            for pattern, parameters in _pages_to_render(renderer):
                for language in get_langs():
                    uri, file_name, _status, _headers, body = render_pattern(
                        pattern, parameters, language
                    )
                    path, _local_uri = get_static_filepath(output_dir, file_name, uri)
                    path = Path(path)
                    # Addresses without a language (data/family.js) are the
                    # same in every language: written once.
                    if path in written:
                        continue
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    written.add(path)
    except DistillError as error:
        raise ExportError(str(error)) from error
    finally:
        # Rendering switches the active language; put it back.
        if language_before:
            translation.activate(language_before)
        else:
            translation.deactivate_all()
    return sum(1 for path in written if path.suffix == ".html")


def _copy_static_files(target: Path) -> None:
    """Copy the site's CSS, JavaScript and icons (not the admin panel's)."""
    for finder in finders.get_finders():
        # The same files Django's collectstatic skips: hidden and backup files.
        for path, storage in finder.list(ignore_patterns=["CVS", ".*", "*~"]):
            # On Windows the path comes with "\" instead of "/".
            if Path(path).parts[0] == "admin":
                continue
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(storage.path(path), destination)


def _write_media(output_dir: Path) -> None:
    """Write the media files the exported pages use, and nothing else.

    Photos are never copied: each address of a smaller copy found in the
    pages ("/media/v/480/photos/x.png.jpg") is made from the original. Clips
    are copied as they are. Originals, unused photos and everything else in
    the media folder stay on the owner's computer.
    """
    media_dir = output_dir / settings.MEDIA_URL.strip("/")
    media_root = Path(settings.MEDIA_ROOT).resolve()
    wanted: set[str] = set()
    for page in list(output_dir.rglob("*.html")) + list(output_dir.rglob("*.js")):
        if media_dir in page.parents:
            continue
        for match in _MEDIA_REFERENCE.finditer(page.read_text(encoding="utf-8")):
            wanted.add(unquote(match["path"]))

    # Only files the database knows can be published: an address typed in a
    # text cannot send any other file of the media folder.
    known_images = set()
    for model, field in ((Person, "photo"), (Photo, "image"), (Recipe, "photo")):
        known_images |= set(model.objects.exclude(**{field: ""}).values_list(field, flat=True))
    known_clips = set(Clip.objects.values_list("file", flat=True))

    problems = []
    for path in sorted(wanted):
        relative = Path(path)
        destination = (media_dir / relative).resolve()
        if ".." in relative.parts or media_dir.resolve() not in destination.parents:
            problems.append(_("Missing file: %(file)s") % {"file": path})
            continue
        if path.startswith(f"{URL_PREFIX}/"):
            parsed = parse_variant_path(path[len(URL_PREFIX) + 1 :])
            if parsed is None or parsed[1] not in known_images:
                problems.append(_("Missing or unreadable photo: %(file)s") % {"file": path})
                continue
            try:
                source = make_variant(parsed[1], parsed[0])
            except VariantError:
                problems.append(_("Missing or unreadable photo: %(file)s") % {"file": path})
                continue
        else:
            source = (media_root / relative).resolve()
            if path not in known_clips or media_root / "clips" not in source.parents or not source.is_file():
                problems.append(_("Missing file: %(file)s") % {"file": path})
                continue
        # The folder is created only after the address was checked.
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if problems:
        raise ExportError(_("Some files used by the pages could not be written."), problems)

def _write_front_door(output_dir: Path) -> None:
    """The index.html at the top: it sends the visitor to the default language."""
    language = settings.LANGUAGE_CODE
    start = f"{language}/index.html"
    (output_dir / "index.html").write_text(
        "<!DOCTYPE html>\n"
        f'<html lang="{language}">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="robots" content="noindex, nofollow">\n'
        f'  <meta http-equiv="refresh" content="0; url={start}">\n'
        "  <title>Raízes</title>\n"
        "</head>\n"
        "<body>\n"
        f'  <p><a href="{start}">Raízes</a></p>\n'
        "</body>\n"
        "</html>\n",
        encoding="utf-8",
    )


def _split_url(url: str) -> tuple[str, str]:
    """Separate the path of a link from its "?query" and "#fragment"."""
    cut = min((url.index(mark) for mark in "?#" if mark in url), default=len(url))
    return url[:cut], url[cut:]


def _make_links_relative(output_dir: Path) -> None:
    """Rewrite links like "/pt-br/people/x/" as "../x/index.html".

    Django writes addresses starting at the root of the server. Relative
    addresses work everywhere: on the hosting, and also when the folder is
    simply opened from the disk, where there is no server.
    """
    for page in output_dir.rglob("*.html"):
        folder = page.parent.relative_to(output_dir).as_posix()

        def relative(match: re.Match) -> str:
            url = match["url"]
            if not url.startswith("/") or url.startswith("//"):
                return match[0]
            path, rest = _split_url(url)
            target = path.lstrip("/")
            if not target or target.endswith("/"):
                target += "index.html"
            return f'{match["attribute"]}="{posixpath.relpath(target, start=folder)}{rest}"'

        html = page.read_text(encoding="utf-8")
        page.write_text(_LINK.sub(relative, html), encoding="utf-8")


def find_dead_links(output_dir: Path) -> list[str]:
    """Links between the exported files that lead to no file."""
    output_dir = Path(output_dir).resolve()
    dead = []
    for page in sorted(output_dir.rglob("*.html")):
        html = page.read_text(encoding="utf-8")
        for match in _LINK.finditer(html):
            url = match["url"]
            if not url or _EXTERNAL.match(url):
                continue
            path, _rest = _split_url(url)
            if not path:
                continue
            if path.startswith("/"):
                target = output_dir / path.lstrip("/")
            else:
                target = page.parent / unquote(path)
            target = target.resolve()
            if not target.is_file() or output_dir not in target.parents:
                dead.append(f"{page.relative_to(output_dir).as_posix()}: {url}")
    return dead

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
from django_distill.request import get_static_filepath
from django_distill.utils import get_langs

from .models import Person
from .textcheck import all_text_problems

# A file left in the exported folder. A folder is only ever erased by the
# export when this file is in it, so no other folder can be wiped by mistake.
MARKER = ".raizes-export"

_LINK = re.compile(r'(?P<attribute>href|src)="(?P<url>[^"]*)"')
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
    _copy_photos(output_dir / settings.MEDIA_URL.strip("/"))
    _write_front_door(output_dir)
    (output_dir / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    _make_links_relative(output_dir)

    dead_links = find_dead_links(output_dir)
    if dead_links:
        raise ExportError(_("The exported site has links to files that do not exist."), dead_links)

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


def _render_pages(output_dir: Path) -> int:
    """Render every page marked with `distill_path=True`, in every language."""
    language_before = translation.get_language()
    pages = 0
    try:
        with DistillRenderer() as renderer:
            for pattern, parameters, _uri in renderer.get_urls_to_render():
                for language in get_langs():
                    uri, file_name, _status, _headers, body = render_pattern(
                        pattern, parameters, language
                    )
                    path, _local_uri = get_static_filepath(output_dir, file_name, uri)
                    path = Path(path)
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(body)
                    pages += 1
    except DistillError as error:
        raise ExportError(str(error)) from error
    finally:
        # Rendering switches the active language; put it back.
        if language_before:
            translation.activate(language_before)
        else:
            translation.deactivate_all()
    return pages


def _copy_static_files(target: Path) -> None:
    """Copy the site's CSS, JavaScript and icons (not the admin panel's)."""
    for finder in finders.get_finders():
        for path, storage in finder.list(ignore_patterns=[]):
            # On Windows the path comes with "\" instead of "/".
            if Path(path).parts[0] == "admin":
                continue
            destination = target / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(storage.path(path), destination)


def _copy_photos(target: Path) -> None:
    """Copy only the photos that the pages show.

    Everything else in the media folder (originals, photos not used yet)
    stays on the owner's computer.
    """
    media_root = Path(settings.MEDIA_ROOT)
    for person in Person.objects.exclude(photo=""):
        source = media_root / person.photo.name
        if source.is_file():
            destination = target / person.photo.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


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

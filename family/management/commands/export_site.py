"""`python manage.py export_site`

Writes the whole site into the dist/ folder as static files. Open
dist/index.html in the browser to see it: Django does not need to be running.
"""
from django.core.management.base import BaseCommand, CommandError
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _

from family.export import ExportError, export_site


class Command(BaseCommand):
    help = "Exports the site as static files into dist/ (or the folder given in --output)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            help="Folder to write the site into. Default: dist/",
        )

    def handle(self, *args, **options):
        try:
            report = export_site(options["output"])
        except ExportError as error:
            lines = [str(error)] + [f"  - {problem}" for problem in error.problems]
            raise CommandError("\n".join(lines)) from error

        self.stdout.write(
            self.style.SUCCESS(
                _("Site exported: %(pages)d pages, %(files)d files, %(size)s.")
                % {
                    "pages": report.pages,
                    "files": report.files,
                    "size": filesizeformat(report.size),
                }
            )
        )
        self.stdout.write(
            _("Open this file in the browser: %(path)s")
            % {"path": report.output_dir / "index.html"}
        )

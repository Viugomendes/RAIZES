"""`python manage.py compile_translations`

Run it after editing a file in locale/: Django only sees the new texts after
the .po files are compiled into .mo files.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from family.pofiles import compile_po_file


class Command(BaseCommand):
    help = "Compiles the translation files in locale/ (.po) into .mo files."

    def handle(self, *args, **options):
        count = 0
        for locale_dir in settings.LOCALE_PATHS:
            for po_path in sorted(Path(locale_dir).glob("*/LC_MESSAGES/*.po")):
                mo_path = compile_po_file(po_path)
                self.stdout.write(f"{po_path} -> {mo_path.name}")
                count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} translation file(s) compiled."))

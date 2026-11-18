"""`python manage.py restaurar <zip>`: puts a backup back in place.

The backup wins: its data folder and its `.env` (family, secret key, e-mail)
replace what is here. What was here is first saved in backups/.
"""
import zipfile
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from access.management.commands.backup import JOURNAL_SUFFIXES, make_backup
from config.env import owner_only

# The data folders a backup can hold, and the database inside each one.
FOLDERS = {"data": "raizes.sqlite3", "demo": "demo.sqlite3"}


class Command(BaseCommand):
    # Translated when argparse reads it (a lazy text crashes `--help`).
    @property
    def help(self):
        return _("Restores a backup made by the backup command.")

    def add_arguments(self, parser):
        parser.add_argument("archive", help=_("The backup .zip file."))

    def unsafe(self, name):
        return CommandError(_("Unsafe path inside the backup: %(name)s") % {"name": name})

    def target(self, name):
        """Where an entry goes. Nothing may land outside the data folders and .env."""
        normalized = name.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if not parts or normalized.startswith("/") or any(":" in part for part in parts) or ".." in parts:
            raise self.unsafe(name)
        if normalized == ".env":
            return settings.ENV_FILE
        if parts[0] in FOLDERS:
            # The data folders sit next to .env, in the project folder.
            folder = Path(settings.ENV_FILE).parent / parts[0]
            target = folder.joinpath(*parts[1:])
            if folder.resolve() not in target.resolve().parents:
                raise self.unsafe(name)
            return target
        raise CommandError(
            _("This backup does not belong here (unexpected entry: %(name)s).") % {"name": name}
        )

    def handle(self, *args, **options):
        archive = Path(options["archive"])
        if not archive.is_file():
            raise CommandError(_("File not found: %(file)s") % {"file": archive})
        try:
            zipped = zipfile.ZipFile(archive)
        except zipfile.BadZipFile:
            raise CommandError(_("This is not a valid backup file."))
        with zipped:
            # Everything is checked before anything is written.
            entries = [(info, self.target(info.filename)) for info in zipped.infolist()]
            if not entries:
                raise CommandError(_("The backup is empty."))
            self.save_what_is_there(entries)
            for info, target in entries:
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                # An old journal next to the restored database would bring old pages back.
                for suffix in JOURNAL_SUFFIXES:
                    Path(f"{target}{suffix}").unlink(missing_ok=True)
                target.write_bytes(zipped.read(info))
                if target == settings.ENV_FILE:
                    owner_only(target)
        self.stdout.write(self.style.SUCCESS(_("Backup restored.")))
        self.stdout.write(_("Start the site again (servir), so it reads the restored .env."))

    def save_what_is_there(self, entries):
        names = {
            PurePosixPath(info.filename.replace("\\", "/")).parts[0]
            for info, target in entries
            if target != settings.ENV_FILE
        }
        for name in sorted(names):
            folder = Path(settings.ENV_FILE).parent / name
            if folder.is_dir() and any(folder.iterdir()):
                saved = make_backup("antes-de-restaurar", folder, folder / FOLDERS[name])
                self.stdout.write(
                    _("What was there before was saved first in %(file)s.") % {"file": saved}
                )

"""`python manage.py restaurar <zip>`: puts a backup back in place."""
import zipfile
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _

from config.env import owner_only


class Command(BaseCommand):
    help = _("Restores a backup made by the backup command.")

    def add_arguments(self, parser):
        parser.add_argument("archive", help=_("The backup .zip file."))
        parser.add_argument(
            "--force", action="store_true", help=_("Overwrite data that is already there.")
        )

    def unsafe(self, name):
        return CommandError(_("Unsafe path inside the backup: %(name)s") % {"name": name})

    def target(self, name):
        """Where an entry goes. Nothing may land outside the data folder and .env."""
        normalized = name.replace("\\", "/")
        parts = PurePosixPath(normalized).parts
        if not parts or normalized.startswith("/") or any(":" in part for part in parts) or ".." in parts:
            raise self.unsafe(name)
        if normalized == ".env":
            return settings.ENV_FILE
        if parts[0] == settings.DATA_DIR.name:
            target = settings.DATA_DIR.joinpath(*parts[1:])
            if settings.DATA_DIR.resolve() not in target.resolve().parents:
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
            if not options["force"]:
                self.check_nothing_is_overwritten(zipped, entries)
            for info, target in entries:
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zipped.read(info))
                if target == settings.ENV_FILE:
                    owner_only(target)
        self.stdout.write(self.style.SUCCESS(_("Backup restored.")))

    def check_nothing_is_overwritten(self, zipped, entries):
        data = settings.DATA_DIR
        if data.is_dir() and any(data.iterdir()):
            raise CommandError(_("The data folder is not empty. Use --force to overwrite it."))
        for info, target in entries:
            if target == settings.ENV_FILE and target.is_file():
                if target.read_bytes() != zipped.read(info):
                    raise CommandError(
                        _(".env already exists and is different. Use --force to overwrite it.")
                    )

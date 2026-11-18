"""`python manage.py backup`: one zip with the data folder and the `.env`."""
import datetime
import sqlite3
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from config.env import owner_only

LEFT_OUT = {"cache"}  # the photo copies are made again on demand
JOURNAL_SUFFIXES = ("-wal", "-shm", "-journal")


def snapshot(source: Path, destination: Path) -> None:
    """A consistent copy of a SQLite file, even while the server writes to it."""
    origin = sqlite3.connect(source)
    copy = sqlite3.connect(destination)
    try:
        origin.backup(copy)
    finally:
        copy.close()
        origin.close()


def make_backup(name: str, data: Path, database: Path) -> Path:
    """Zip the data folder and .env into backups/<name>-YYYY-MM-DD-HHMMSS.zip."""
    env = settings.ENV_FILE
    folder = settings.RAIZES_BACKUP_DIR
    folder.mkdir(parents=True, exist_ok=True)
    owner_only(folder, 0o700)
    archive = folder / f"{name}-{datetime.datetime.now():%Y-%m-%d-%H%M%S}.zip"
    try:
        # Mode "x": an existing backup is never overwritten.
        zipped = zipfile.ZipFile(archive, "x", zipfile.ZIP_DEFLATED)
    except FileExistsError:
        raise CommandError(
            _("A backup with this name already exists. Wait a second and try again.")
        )
    database = database.resolve()
    try:
        # Before anything is written: the zip holds the secrets of .env.
        owner_only(archive)
        with zipped, tempfile.TemporaryDirectory() as temp:
            for path in sorted(data.rglob("*")):
                relative = path.relative_to(data)
                if relative.parts[0] in LEFT_OUT or not path.is_file():
                    continue
                if path.name.endswith(JOURNAL_SUFFIXES):
                    continue
                source = path
                # Only the database needs the SQLite snapshot.
                if path.resolve() == database:
                    source = Path(temp) / "snapshot.db"
                    snapshot(path, source)
                zipped.write(source, f"{data.name}/{relative.as_posix()}")
                if source is not path:
                    source.unlink()
            if env.is_file():
                zipped.write(env, ".env")
    except Exception as error:
        archive.unlink(missing_ok=True)
        raise CommandError(
            _("The backup failed (%(error)s). Nothing was saved.") % {"error": error}
        )
    return archive


class Command(BaseCommand):
    # Translated when argparse reads it (a lazy text crashes `--help`).
    @property
    def help(self):
        return _("Saves the data folder and .env into backups/raizes-YYYY-MM-DD-HHMMSS.zip.")

    def handle(self, *args, **options):
        archive = make_backup("raizes", settings.DATA_DIR, Path(settings.DATABASE_FILE))
        self.stdout.write(self.style.SUCCESS(_("Backup saved: %(file)s") % {"file": archive}))
        self.stdout.write(_("It holds private data and passwords: keep it in a safe place."))

"""`python manage.py backup`: one zip with the data folder and the `.env`."""
import datetime
import zipfile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _

LEFT_OUT = {"cache"}  # the photo copies are made again on demand


class Command(BaseCommand):
    help = _("Saves the data folder and .env into backups/raizes-YYYY-MM-DD-HHMM.zip.")

    def handle(self, *args, **options):
        data = settings.DATA_DIR
        env = settings.ENV_FILE
        folder = settings.RAIZES_BACKUP_DIR
        folder.mkdir(parents=True, exist_ok=True)
        archive = folder / f"raizes-{datetime.datetime.now():%Y-%m-%d-%H%M}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for path in sorted(data.rglob("*")):
                relative = path.relative_to(data)
                if relative.parts[0] in LEFT_OUT or not path.is_file():
                    continue
                zipped.write(path, f"{data.name}/{relative.as_posix()}")
            if env.is_file():
                zipped.write(env, ".env")
        self.stdout.write(self.style.SUCCESS(_("Backup saved: %(file)s") % {"file": archive}))
        self.stdout.write(_("It holds private data and passwords: keep it in a safe place."))

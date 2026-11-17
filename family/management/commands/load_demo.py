"""`python manage.py load_demo`

Creates the database if needed and fills it with the invented family of
demo/family.toml. It only works with the demo dataset, so it can never erase
the real family.
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from access.models import SiteSettings
from family.demo import load_demo_family

# The invented family opens locally behind the view password; it is public on purpose.
DEMO_VIEW_PASSWORD = "demo-raizes"


class Command(BaseCommand):
    help = "Loads the invented family of demo/family.toml (replacing what is there)."

    def handle(self, *args, **options):
        if settings.RAIZES_DATASET != "demo":
            raise CommandError(
                _(
                    "This command erases the database before loading the invented "
                    "family, so it only runs with RAIZES_DATASET=demo. The real "
                    "family was not touched."
                )
            )
        call_command("migrate", interactive=False, verbosity=0)
        counts = load_demo_family()
        self.stdout.write(
            self.style.SUCCESS(
                _(
                    "Invented family loaded: %(people)d people, %(unions)d unions, "
                    "%(places)d places, %(photos)d photos, %(clips)d recordings, "
                    "%(recipes)d recipes."
                )
                % counts
            )
        )
        SiteSettings.get().set_view_password(DEMO_VIEW_PASSWORD)
        self.stdout.write(
            _("Password to open the invented family: %(password)s")
            % {"password": DEMO_VIEW_PASSWORD}
        )

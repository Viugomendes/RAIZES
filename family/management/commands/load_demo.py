"""`python manage.py load_demo`

Creates the database if needed and fills it with the invented family of
demo/family.toml. It only works with the demo dataset, so it can never erase
the real family.
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _

from family.demo import load_demo_family


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
                    "%(places)d places, %(recipes)d recipes."
                )
                % counts
            )
        )

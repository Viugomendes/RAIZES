"""`python manage.py instalar`: first-time setup, asking a few questions.

Writes the family (real, or the invented one with --demo), the language and
the family name in `.env`, sets the view password, creates the owner's account
and e-mails its generated password.
"""
import getpass
import os
import subprocess
import sys

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import translation
from django.utils.translation import gettext as _

from access.models import SiteSettings
from access.passwords import generate_admin_password
from config.env import set_env_values

MIN_VIEW_PASSWORD = 8


class Command(BaseCommand):
    # Translated when argparse reads it (a lazy text crashes `--help`).
    @property
    def help(self):
        return _("Sets up Raízes: language, family name, view password and the owner's account.")

    def add_arguments(self, parser):
        parser.add_argument("--family-name", help=_("Name of the family."))
        parser.add_argument("--language", help=_("Language of the site: pt-br or es."))
        parser.add_argument("--email", help=_("E-mail of the owner (it receives the password)."))
        parser.add_argument(
            "--view-password", help=_("Password the family types to open the site (8+ characters).")
        )
        parser.add_argument(
            "--no-input", action="store_true", help=_("Never ask: every option is required.")
        )
        parser.add_argument(
            "--demo",
            action="store_true",
            help=_("Install the invented family (demo/) instead of the real one (data/)."),
        )

    def handle(self, *args, **options):
        dataset = "demo" if options["demo"] else "real"
        if settings.RAIZES_DATASET != dataset:
            # The settings (database, folders) were read when the command started:
            # run again, in a new process, with the right family.
            return self.run_again(dataset, options)
        # A fresh copy of the project has no database yet.
        call_command("migrate", interactive=False, verbosity=0)
        values = self.collect(options)
        family_name, language, email, view_password = values
        self.validate(language, email, view_password)

        # First, so that a failure here leaves no account whose password was never shown.
        try:
            set_env_values(
                settings.ENV_FILE,
                {
                    "RAIZES_DATASET": dataset,
                    "RAIZES_LANGUAGE": language,
                    "RAIZES_FAMILY_NAME": family_name,
                    # The site is going to be served to the family: no debug mode.
                    "RAIZES_DEBUG": "false",
                },
            )
        except (OSError, ValueError) as error:
            raise CommandError(
                _(".env could not be written (%(error)s). Nothing was installed.")
                % {"error": error}
            )
        user_model = get_user_model()
        admin_password = generate_admin_password()
        user_model.objects.create_superuser(email, email=email, password=admin_password)
        site = SiteSettings.get()
        site.family_name = family_name
        site.save(update_fields=["family_name"])
        site.set_view_password(view_password)
        self.stdout.write(self.style.SUCCESS(_("Installed. The site opens in the chosen language.")))
        self.send_password(email, admin_password, language)

    def run_again(self, dataset, options):
        command = [sys.executable, "-m", "django", "instalar"]
        for name in ("family_name", "language", "email", "view_password"):
            if options[name]:
                command += ["--" + name.replace("_", "-"), options[name]]
        command += ["--no-input"] * options["no_input"] + ["--demo"] * options["demo"]
        result = subprocess.run(
            command, cwd=settings.BASE_DIR, env={**os.environ, "RAIZES_DATASET": dataset}
        )
        if result.returncode:
            raise CommandError(_("The installation did not finish (see the message above)."))

    def collect(self, options):
        names = ("family_name", "language", "email", "view_password")
        if options["no_input"]:
            if not all(options[name] for name in names):
                raise CommandError(
                    _("With --no-input, give --family-name, --language, --email and --view-password.")
                )
            return [options[name].strip() for name in names[:3]] + [options["view_password"]]
        family_name = options["family_name"] or input(str(_("Family name: ")))
        language = options["language"] or input(str(_("Language (pt-br or es): ")))
        email = options["email"] or input(str(_("Your e-mail (the panel login): ")))
        view_password = options["view_password"]
        if not view_password:
            view_password = getpass.getpass(str(_("Family view password (8+ characters): ")))
            if getpass.getpass(str(_("Type it again: "))) != view_password:
                raise CommandError(_("The two passwords are not the same."))
        return family_name.strip(), language.strip().lower(), email.strip(), view_password

    def validate(self, language, email, view_password):
        if language not in dict(settings.LANGUAGES):
            raise CommandError(
                _("Language must be one of: %(options)s")
                % {"options": ", ".join(dict(settings.LANGUAGES))}
            )
        if "@" not in email or " " in email:
            raise CommandError(_("Type a valid e-mail."))
        if len(view_password.strip()) < MIN_VIEW_PASSWORD:
            raise CommandError(
                _("The view password needs at least %(count)d characters.")
                % {"count": MIN_VIEW_PASSWORD}
            )
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=email).exists() or user_model.objects.filter(
            username__iexact=email
        ).exists():
            raise CommandError(_("There is already an account with this e-mail."))

    def send_password(self, email, password, language):
        try:
            if not settings.RAIZES_EMAIL_CONFIGURED:
                # The e-mail would only be written to a file in DATA_DIR/emails.
                raise OSError("e-mail is not configured")
            with translation.override(language):
                send_mail(
                    str(_("Your Raízes panel password")),
                    str(
                        _(
                            "Hello!\n\nThe panel is at /painel/. Log in with this e-mail and "
                            "this password:\n\n%(password)s\n\nKeep it safe."
                        )
                    )
                    % {"password": password},
                    None,
                    [email],
                )
        except Exception:
            # Shown once, here only: never logged.
            self.stdout.write(
                _(
                    "The e-mail could not be sent (e-mail is not configured yet; see the "
                    "README, section about e-mail). Write this panel password down now, "
                    "it will not be shown again:"
                )
            )
            self.stdout.write(password)
            return
        self.stdout.write(_("The panel password was sent to %(email)s.") % {"email": email})

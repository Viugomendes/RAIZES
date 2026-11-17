"""Family name and central person: the panel's value wins, else the .env one."""
from django.conf import settings

from .models import SiteSettings


def family_name() -> str:
    return SiteSettings.get().family_name or settings.RAIZES_FAMILY_NAME


def central_person_identifier() -> str | None:
    person = SiteSettings.get().central_person
    return person.identifier if person else settings.RAIZES_CENTRAL_PERSON

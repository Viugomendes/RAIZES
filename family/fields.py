"""Custom field types used by the models."""
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .dates import PartialDate


class PartialDateField(models.CharField):
    """A date that may be complete or only a year.

    It is stored as text: "1962" or "1962-03-14". Typing "14/03/1962" is also
    accepted and converted. Empty means unknown.
    """

    description = "Date that may be only a year"
    default_error_messages = {
        "invalid_date": _("Write the date as DD/MM/YYYY or just the year (YYYY)."),
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 10)
        kwargs.setdefault("blank", True)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return ""
        try:
            return str(PartialDate.parse(value))
        except ValueError:
            raise ValidationError(
                self.error_messages["invalid_date"], code="invalid_date"
            ) from None


def parse_stored_date(value: str) -> PartialDate | None:
    """Read a stored date; text that is not a valid date counts as unknown."""
    try:
        return PartialDate.parse(value)
    except ValueError:
        return None

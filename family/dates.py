"""Dates that may be complete (day, month and year) or only a year.

Family history is full of dates nobody remembers exactly, so a person's birth
can be recorded as "1962" as well as "14/03/1962".
"""
import datetime
import re
from dataclasses import dataclass
from functools import total_ordering

from django.utils.dates import MONTHS
from django.utils.translation import gettext as _

_YEAR = re.compile(r"^(\d{4})$")
_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DAY_FIRST = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")

MIN_YEAR = 1000


@total_ordering
@dataclass(frozen=True)
class PartialDate:
    year: int
    month: int | None = None
    day: int | None = None

    @classmethod
    def parse(cls, text: str | None) -> "PartialDate | None":
        """Read "1962", "1962-03-14" or "14/03/1962". Empty text means unknown.

        Raises ValueError when the text is not one of those formats or the day
        does not exist in the calendar.
        """
        text = (text or "").strip()
        if not text:
            return None
        if match := _YEAR.match(text):
            year, month, day = int(match[1]), None, None
        elif match := _ISO.match(text):
            year, month, day = int(match[1]), int(match[2]), int(match[3])
        elif match := _DAY_FIRST.match(text):
            day, month, year = int(match[1]), int(match[2]), int(match[3])
        else:
            raise ValueError(f"not a date: {text!r}")
        if year < MIN_YEAR:
            raise ValueError(f"year out of range: {text!r}")
        if month is not None:
            datetime.date(year, month, day)  # raises ValueError if impossible
        return cls(year, month, day)

    @property
    def is_complete(self) -> bool:
        return self.month is not None

    def __str__(self) -> str:
        """The text stored in the database: "1962" or "1962-03-14"."""
        if self.is_complete:
            return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"
        return f"{self.year:04d}"

    def _sort_key(self) -> tuple[int, int, int]:
        return (self.year, self.month or 0, self.day or 0)

    def __lt__(self, other: "PartialDate") -> bool:
        if not isinstance(other, PartialDate):
            return NotImplemented
        return self._sort_key() < other._sort_key()

    def is_surely_before(self, other: "PartialDate") -> bool:
        """True only when this date is certainly earlier than the other.

        When one of them is just a year, only the years are compared: someone
        born on 14/03/1962 may well have died "in 1962".
        """
        if self.is_complete and other.is_complete:
            return self._sort_key() < other._sort_key()
        return self.year < other.year

    def display(self, approximate: bool = False) -> str:
        """The date as shown on the site, in the active language."""
        if approximate:
            return f"c. {self.year}"
        if not self.is_complete:
            return str(self.year)
        # Portuguese and Spanish write month names in lowercase, but Django's
        # Portuguese month names are capitalised, so the case is fixed here.
        return _("%(day)d %(month)s %(year)d") % {
            "day": self.day,
            "month": str(MONTHS[self.month]).lower(),
            "year": self.year,
        }

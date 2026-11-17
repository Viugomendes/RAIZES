"""The data of the family.

Only facts are stored here. Parents, siblings, children and grandchildren are
never typed in: they are calculated from the unions (see kinship.py).
"""
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .fields import PartialDateField, parse_stored_date
from .identifiers import is_valid_identifier, suggest_identifier
from .youtube import extract_video_id

# The free texts of a person's page: (field name, title of the section).
# They are sections 2 to 9 of the page; sections 1 and 10 are built by the site.
TEXT_SECTIONS = (
    ("tastes", _("Tastes and quirks")),
    ("childhood", _("Childhood and youth")),
    ("work", _("Work and adult life")),
    ("love", _("Love and friendship")),
    ("origins", _("Origins and times")),
    ("memories", _("Memories and reflections")),
    ("legacy", _("Legacy")),
    ("remembrance", _("In the memory of others")),
)

MARKDOWN_HELP = _(
    "Optional. Written in Markdown. [[identifier]] links to a person and "
    "[mm:ss] links to that minute of the interview."
)


def validate_youtube_url(value: str) -> None:
    if extract_video_id(value) is None:
        raise ValidationError(
            _(
                "Paste the link of the video on YouTube, in one of these formats: "
                "https://www.youtube.com/watch?v=CODE or https://youtu.be/CODE."
            ),
            code="invalid_youtube_url",
        )


class Place(models.Model):
    """A place, written once and reused in every person and photo."""

    slug = models.SlugField(
        _("identifier"),
        unique=True,
        help_text=_("Short name used in links, for example: valencia."),
    )
    name = models.CharField(
        _("name"), max_length=200, help_text=_("For example: Valência, Espanha.")
    )
    latitude = models.FloatField(
        _("latitude"),
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.FloatField(
        _("longitude"),
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("place")
        verbose_name_plural = _("places")

    def __str__(self):
        return self.name

    def clean(self):
        if (self.latitude is None) != (self.longitude is None):
            missing = "latitude" if self.latitude is None else "longitude"
            raise ValidationError(
                {missing: _("Fill in both latitude and longitude, or neither.")}
            )


class Person(models.Model):
    class Sex(models.TextChoices):
        FEMALE = "f", _("Female")
        MALE = "m", _("Male")
        OTHER = "x", _("Other")

    identifier = models.CharField(
        _("identifier"),
        max_length=80,
        unique=True,
        blank=True,
        help_text=_(
            "Format name-surname-year, for example: ramon-garcia-1962. Leave it "
            "empty to have it created for you. It never changes afterwards."
        ),
    )
    given_name = models.CharField(_("given name"), max_length=100)
    surname = models.CharField(_("surname"), max_length=150, blank=True)
    nickname = models.CharField(_("nickname"), max_length=100, blank=True)
    other_names = models.CharField(
        _("other names"),
        max_length=300,
        blank=True,
        help_text=_("Maiden name, other spellings. Separate them with commas."),
    )
    sex = models.CharField(_("sex"), max_length=1, choices=Sex.choices, blank=True)

    birth_date = PartialDateField(
        _("birth date"),
        help_text=_("Complete (14/03/1962) or just the year (1962). Empty if unknown."),
    )
    birth_date_approximate = models.BooleanField(
        _("approximate birth date"),
        default=False,
        help_text=_('The site shows "c. 1962".'),
    )
    birth_place = models.ForeignKey(
        Place,
        verbose_name=_("birth place"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="people_born",
    )

    deceased = models.BooleanField(
        _("deceased"),
        default=False,
        help_text=_("Tick it when the person has died, even if the date is unknown."),
    )
    death_date = PartialDateField(_("death date"))
    death_date_approximate = models.BooleanField(_("approximate death date"), default=False)
    death_place = models.ForeignKey(
        Place,
        verbose_name=_("death place"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="people_died",
    )
    resting_place = models.ForeignKey(
        Place,
        verbose_name=_("resting place"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="people_resting",
    )

    lives_in = models.ForeignKey(
        Place,
        verbose_name=_("lives in"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="residents",
        help_text=_("Only the city, never the full address."),
    )
    lived_in = models.ManyToManyField(
        Place, verbose_name=_("lived in"), blank=True, related_name="former_residents"
    )
    occupation = models.CharField(_("occupation"), max_length=200, blank=True)
    tags = models.CharField(
        _("tags"),
        max_length=300,
        blank=True,
        help_text=_("Free words separated by commas, for example: musician, emigrant."),
    )

    photo = models.ImageField(_("main photo"), upload_to="people/", blank=True)
    interview_url = models.URLField(
        _("interview link"),
        blank=True,
        validators=[validate_youtube_url],
        help_text=_(
            "Normal link of the video on YouTube: "
            "https://www.youtube.com/watch?v=CODE or https://youtu.be/CODE."
        ),
    )

    confirmed = models.BooleanField(
        _("confirmed"),
        default=True,
        help_text=_("Untick it while the information about this person is doubtful."),
    )
    source = models.CharField(
        _("source"),
        max_length=300,
        blank=True,
        help_text=_("Where the information came from, for example: told by aunt Marta."),
    )

    tastes = models.TextField(TEXT_SECTIONS[0][1], blank=True, help_text=MARKDOWN_HELP)
    childhood = models.TextField(TEXT_SECTIONS[1][1], blank=True, help_text=MARKDOWN_HELP)
    work = models.TextField(TEXT_SECTIONS[2][1], blank=True, help_text=MARKDOWN_HELP)
    love = models.TextField(TEXT_SECTIONS[3][1], blank=True, help_text=MARKDOWN_HELP)
    origins = models.TextField(TEXT_SECTIONS[4][1], blank=True, help_text=MARKDOWN_HELP)
    memories = models.TextField(TEXT_SECTIONS[5][1], blank=True, help_text=MARKDOWN_HELP)
    legacy = models.TextField(TEXT_SECTIONS[6][1], blank=True, help_text=MARKDOWN_HELP)
    remembrance = models.TextField(TEXT_SECTIONS[7][1], blank=True, help_text=MARKDOWN_HELP)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        ordering = ["given_name", "surname", "identifier"]
        verbose_name = _("person")
        verbose_name_plural = _("people")

    def __str__(self):
        return self.full_name

    def get_absolute_url(self) -> str:
        """Address of the person's page on the site."""
        return reverse("family:person_detail", args=[self.identifier])

    # ----- Calculated values -------------------------------------------------

    @property
    def full_name(self) -> str:
        return f"{self.given_name} {self.surname}".strip()

    @property
    def initials(self) -> str:
        """First letters of the given name and of the last surname: "RO"."""
        last_surname = self.surname.split()[-1:] or [""]
        return (self.given_name[:1] + last_surname[0][:1]).upper()

    @property
    def birth(self):
        """The birth date as a PartialDate, or None if unknown."""
        return parse_stored_date(self.birth_date)

    @property
    def death(self):
        return parse_stored_date(self.death_date)

    @property
    def birth_year(self) -> int | None:
        return self.birth.year if self.birth else None

    @property
    def is_deceased(self) -> bool:
        return self.deceased or bool(self.death_date)

    @property
    def birth_display(self) -> str:
        return self.birth.display(self.birth_date_approximate) if self.birth else ""

    @property
    def death_display(self) -> str:
        return self.death.display(self.death_date_approximate) if self.death else ""

    @property
    def years_display(self) -> str:
        """Short form for lists and the tree: "1962", "1900–1980", "c. 1885–?"."""
        born = ""
        if self.birth:
            born = ("c. " if self.birth_date_approximate else "") + str(self.birth.year)
        died = ""
        if self.death:
            died = ("c. " if self.death_date_approximate else "") + str(self.death.year)
        if not self.is_deceased:
            return born
        if not born and not died:
            return ""
        return f"{born or '?'}–{died or '?'}"

    @property
    def tag_list(self) -> list[str]:
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]

    @property
    def youtube_id(self) -> str | None:
        return extract_video_id(self.interview_url) if self.interview_url else None

    # ----- Validation and saving ---------------------------------------------

    def _stored_identifier(self) -> str | None:
        if self.pk is None:
            return None
        return Person.objects.filter(pk=self.pk).values_list("identifier", flat=True).first()

    def _new_identifier(self) -> str:
        return suggest_identifier(
            self.given_name,
            self.surname,
            self.birth_year,
            lambda candidate: Person.objects.filter(identifier=candidate).exists(),
        )

    def clean(self):
        errors = {}

        stored = self._stored_identifier()
        if stored is not None and self.identifier != stored:
            errors["identifier"] = _(
                "The identifier cannot change after the person is created: "
                "every link to this person depends on it."
            )
        elif not self.identifier:
            self.identifier = self._new_identifier()
        elif not is_valid_identifier(self.identifier):
            errors["identifier"] = _(
                "Use only lowercase letters without accents, digits and hyphens, "
                "for example: ramon-garcia-1962."
            )

        if self.birth and self.death and self.death.is_surely_before(self.birth):
            errors["death_date"] = _("The death date is before the birth date.")

        if self.death_date:
            self.deceased = True

        # "Músico, emigrante ,músico" -> "músico, emigrante"
        tidy_tags = dict.fromkeys(" ".join(tag.split()).lower() for tag in self.tag_list)
        self.tags = ", ".join(tidy_tags)

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        stored = self._stored_identifier()
        if stored is not None and self.identifier != stored:
            raise ValueError(
                f"The identifier of a person never changes ({stored!r} -> {self.identifier!r})."
            )
        if not self.identifier:
            self.identifier = self._new_identifier()
        if self.death_date:
            self.deceased = True
        super().save(*args, **kwargs)


class Union(models.Model):
    """A relationship between two people. Children hang from the union.

    When one of the parents is unknown, the union has only one partner.
    """

    class Kind(models.TextChoices):
        MARRIAGE = "marriage", _("Marriage")
        PARTNERSHIP = "partnership", _("Partnership")
        DATING = "dating", _("Dating")

    partner1 = models.ForeignKey(
        Person,
        verbose_name=_("first partner"),
        on_delete=models.PROTECT,
        related_name="unions_as_partner1",
    )
    partner2 = models.ForeignKey(
        Person,
        verbose_name=_("second partner"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="unions_as_partner2",
        help_text=_("Leave it empty when the other parent is unknown."),
    )
    kind = models.CharField(
        _("kind"),
        max_length=20,
        choices=Kind.choices,
        blank=True,
        help_text=_("Leave it empty if you do not know."),
    )
    start_date = PartialDateField(
        _("start"), help_text=_("Complete date or just the year. Empty if unknown.")
    )
    end_date = PartialDateField(
        _("end"), help_text=_("Empty means the union is still current.")
    )
    ended = models.BooleanField(
        _("ended"),
        default=False,
        help_text=_("Tick it when the union ended, even if the date is unknown."),
    )
    story = models.TextField(
        _("story of the couple"),
        blank=True,
        help_text=_(
            'Optional, in Markdown. It appears in the section "Love and '
            'friendship" of both partners.'
        ),
    )

    class Meta:
        ordering = ["start_date", "id"]
        verbose_name = _("union")
        verbose_name_plural = _("unions")

    def __str__(self):
        if self.partner2_id is None:
            return _("%(name)s (other parent unknown)") % {"name": self.partner1}
        return f"{self.partner1} & {self.partner2}"

    @property
    def partners(self) -> list[Person]:
        """The one or two known partners."""
        return [self.partner1] + ([self.partner2] if self.partner2_id else [])

    def partner_of(self, person: Person) -> Person | None:
        """The other partner, or None when unknown."""
        if self.partner2_id is None:
            return None
        return self.partner2 if person.pk == self.partner1_id else self.partner1

    @property
    def start(self):
        return parse_stored_date(self.start_date)

    @property
    def end(self):
        return parse_stored_date(self.end_date)

    @property
    def is_ended(self) -> bool:
        return self.ended or bool(self.end_date)

    def clean(self):
        errors = {}
        if self.partner1_id is not None and self.partner1_id == self.partner2_id:
            errors["partner2"] = _("A union needs two different people.")
        if self.start and self.end and self.end.is_surely_before(self.start):
            errors["end_date"] = _("The end is before the start.")
        if self.end_date:
            self.ended = True
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.end_date:
            self.ended = True
        super().save(*args, **kwargs)


def ancestor_ids(person_ids: set[int]) -> set[int]:
    """Ids of every parent, grandparent, etc. of the given people."""
    found: set[int] = set()
    frontier = set(person_ids)
    while frontier:
        rows = ChildLink.objects.filter(child_id__in=frontier).values_list(
            "union__partner1_id", "union__partner2_id"
        )
        parents = {parent for row in rows for parent in row if parent is not None}
        frontier = parents - found
        found |= frontier
    return found


class ChildLink(models.Model):
    """Says that a person is a child of a union, and in which way.

    A person may be a child in more than one union: that is how someone with a
    mother, a father and a stepfather is recorded.
    """

    class Kind(models.TextChoices):
        BIOLOGICAL = "biological", _("Biological")
        ADOPTIVE = "adoptive", _("Adoptive")
        FOSTER = "foster", _("Raised by (stepchild or foster child)")

    union = models.ForeignKey(
        Union, verbose_name=_("union"), on_delete=models.CASCADE, related_name="child_links"
    )
    child = models.ForeignKey(
        Person, verbose_name=_("child"), on_delete=models.CASCADE, related_name="parent_links"
    )
    kind = models.CharField(
        _("kind of link"), max_length=20, choices=Kind.choices, default=Kind.BIOLOGICAL
    )

    class Meta:
        ordering = ["child__birth_date", "id"]
        verbose_name = _("child")
        verbose_name_plural = _("children")
        constraints = [
            models.UniqueConstraint(
                fields=["union", "child"],
                name="unique_child_per_union",
                violation_error_message=_("This person is already a child of this union."),
            )
        ]

    def __str__(self):
        return f"{self.child} ← {self.union}"

    def clean(self):
        try:
            union = self.union
        except Union.DoesNotExist:
            return  # no union chosen yet: the form reports the missing field
        if self.child_id is None:
            return
        partner_ids = {union.partner1_id, union.partner2_id} - {None}
        if self.child_id in partner_ids:
            raise ValidationError(
                {"child": _("A person cannot be a child of their own union.")}
            )
        if self.child_id in ancestor_ids(partner_ids):
            raise ValidationError(
                {
                    "child": _(
                        "This person is an ancestor of one of the partners, "
                        "so cannot also be their child."
                    )
                }
            )


class Photo(models.Model):
    """A photo of the gallery, with the people who appear in it."""

    image = models.ImageField(
        _("file"),
        upload_to="photos/",
        help_text=_(
            "The original stays on this computer. The site only receives smaller "
            "copies, without the hidden data of the file (camera, GPS)."
        ),
    )
    date = PartialDateField(
        _("date"),
        help_text=_("When it was taken: complete (14/03/1962) or just the year. Empty if unknown."),
    )
    place = models.ForeignKey(
        Place,
        verbose_name=_("place"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="photos",
    )
    caption = models.CharField(_("caption"), max_length=300, blank=True)
    people = models.ManyToManyField(
        Person, verbose_name=_("people in the photo"), blank=True, related_name="photos"
    )
    has_unidentified_people = models.BooleanField(
        _("someone not identified"),
        default=False,
        help_text=_('Tick it when someone in the photo is unknown ("Who is this?").'),
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]
        verbose_name = _("photo")
        verbose_name_plural = _("photos")

    def __str__(self):
        return self.caption or self.image.name

    @property
    def taken(self):
        return parse_stored_date(self.date)


# Clips are copied to the site as they are, so they must be small.
CLIP_MAX_BYTES = 25 * 1024 * 1024  # the limit of one file on Cloudflare Pages
AUDIO_EXTENSIONS = ("mp3", "m4a", "ogg", "oga", "wav")
VIDEO_EXTENSIONS = ("mp4", "webm")


def validate_clip_size(file) -> None:
    if file.size > CLIP_MAX_BYTES:
        raise ValidationError(
            _(
                "The file is too big for the site (maximum 25 MB). Long interviews "
                "go on YouTube as unlisted videos."
            ),
            code="clip_too_big",
        )


class Clip(models.Model):
    """A short audio or video recording, shown inside the site."""

    file = models.FileField(
        _("file"),
        upload_to="clips/",
        validators=[
            FileExtensionValidator(AUDIO_EXTENSIONS + VIDEO_EXTENSIONS),
            validate_clip_size,
        ],
        help_text=_(
            "Audio (mp3, m4a, ogg, wav) or short video (mp4, webm), up to 25 MB. "
            "Long interviews go on YouTube."
        ),
    )
    caption = models.CharField(_("caption"), max_length=300, blank=True)
    date = PartialDateField(_("date"))
    people = models.ManyToManyField(
        Person, verbose_name=_("people in the recording"), blank=True, related_name="clips"
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["date", "id"]
        verbose_name = _("audio or video clip")
        verbose_name_plural = _("audio and video clips")

    def __str__(self):
        return self.caption or self.file.name

    @property
    def taken(self):
        return parse_stored_date(self.date)

    @property
    def is_video(self) -> bool:
        return self.file.name.lower().rsplit(".", 1)[-1] in VIDEO_EXTENSIONS


class Recipe(models.Model):
    slug = models.SlugField(
        _("identifier"),
        unique=True,
        help_text=_("Short name used in links, for example: feijoada-da-vo."),
    )
    title = models.CharField(_("title"), max_length=200)
    author = models.ForeignKey(
        Person,
        verbose_name=_("whose recipe it is"),
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="recipes",
    )
    photo = models.ImageField(_("photo"), upload_to="recipes/", blank=True)
    text = models.TextField(
        _("ingredients and preparation"), blank=True, help_text=_("Written in Markdown.")
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        ordering = ["title"]
        verbose_name = _("recipe")
        verbose_name_plural = _("recipes")

    def __str__(self):
        return self.title

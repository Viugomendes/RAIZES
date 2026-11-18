"""Site settings (one row) and the devices that unlocked the family view."""
import datetime
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models import F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

ONLINE_WINDOW = datetime.timedelta(minutes=5)


class SiteSettings(models.Model):
    """Settings the owner edits in the panel. There is only ever one row (pk=1)."""

    family_name = models.CharField(_("family name"), max_length=120, blank=True)
    central_person = models.ForeignKey(
        "family.Person",
        verbose_name=_("central person"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    # Only the hash is stored, never the password itself.
    view_password_hash = models.CharField(_("view password (hash)"), max_length=200, blank=True)
    # Raised on every password change: devices with an older number are locked out.
    password_version = models.PositiveIntegerField(_("password number"), default=1)

    class Meta:
        verbose_name = _("site settings")
        verbose_name_plural = _("site settings")

    def __str__(self) -> str:
        return str(self.family_name or self._meta.verbose_name)

    @classmethod
    def get(cls) -> "SiteSettings":
        # Read on every request (view password, header): one query with the person.
        settings_row, _created = cls.objects.select_related("central_person").get_or_create(pk=1)
        return settings_row

    def set_view_password(self, raw: str) -> None:
        if not raw or not raw.strip():
            raise ValueError("The view password cannot be empty.")
        if self.pk is None:
            self.save()
        # In the database, so a stale instance loses no bump and overwrites no other field.
        type(self).objects.filter(pk=self.pk).update(
            view_password_hash=make_password(raw), password_version=F("password_version") + 1
        )
        self.refresh_from_db(fields=["view_password_hash", "password_version"])

    def check_view_password(self, raw: str) -> bool:
        return bool(self.view_password_hash) and check_password(raw, self.view_password_hash)

    @property
    def has_view_password(self) -> bool:
        return bool(self.view_password_hash)


class ViewerDevice(models.Model):
    """A browser that typed the family password."""

    id = models.UUIDField(_("device code"), primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=80, blank=True)
    browser = models.CharField(_("browser"), max_length=80, blank=True)
    # Only the start of the address, to respect privacy.
    ip_prefix = models.CharField(_("Network (start of the IP)"), max_length=40, blank=True)
    password_version = models.PositiveIntegerField(_("password number"))
    created_at = models.DateTimeField(_("Entered"), auto_now_add=True)
    last_seen = models.DateTimeField(_("Last visit"), default=timezone.now)
    revoked = models.BooleanField(_("revoked"), default=False)

    class Meta:
        verbose_name = _("viewer device")
        verbose_name_plural = _("viewer devices")
        ordering = ["-last_seen"]

    @property
    def is_online(self) -> bool:
        return timezone.now() - self.last_seen <= ONLINE_WINDOW

    def is_valid_for(self, password_version: int) -> bool:
        """The one rule: not revoked, and typed with the current password."""
        return not self.revoked and self.password_version == password_version

    def is_valid(self, site: SiteSettings) -> bool:
        return self.is_valid_for(site.password_version)

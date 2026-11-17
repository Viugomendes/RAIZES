"""Site settings (one row) and the devices that unlocked the family view."""
import datetime
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.db import models
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
    view_password_hash = models.CharField(max_length=200, blank=True)
    # Raised on every password change: devices with an older number are locked out.
    password_version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = _("site settings")
        verbose_name_plural = _("site settings")

    @classmethod
    def get(cls) -> "SiteSettings":
        # Read on every request (view password, header): one query with the person.
        settings_row, _created = cls.objects.select_related("central_person").get_or_create(pk=1)
        return settings_row

    def set_view_password(self, raw: str) -> None:
        self.view_password_hash = make_password(raw)
        self.password_version += 1
        self.save()

    def check_view_password(self, raw: str) -> bool:
        return bool(self.view_password_hash) and check_password(raw, self.view_password_hash)

    @property
    def has_view_password(self) -> bool:
        return bool(self.view_password_hash)


class ViewerDevice(models.Model):
    """A browser that typed the family password."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=80, blank=True)
    browser = models.CharField(_("browser"), max_length=80, blank=True)
    # Only the start of the address, to respect privacy.
    ip_prefix = models.CharField(max_length=40, blank=True)
    password_version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(default=timezone.now)
    revoked = models.BooleanField(_("revoked"), default=False)

    class Meta:
        verbose_name = _("viewer device")
        verbose_name_plural = _("viewer devices")
        ordering = ["-last_seen"]

    @property
    def is_online(self) -> bool:
        return timezone.now() - self.last_seen <= ONLINE_WINDOW

    def is_valid(self, site: SiteSettings) -> bool:
        return not self.revoked and self.password_version == site.password_version

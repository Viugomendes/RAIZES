"""Forms of the panel."""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import SiteSettings

PASSWORD_MIN_LENGTH = 8


class SiteSettingsForm(forms.ModelForm):
    new_view_password = forms.CharField(
        label=_("New family password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Leave empty to keep the current password. Minimum 8 characters."),
    )
    repeat_view_password = forms.CharField(
        label=_("Repeat the new password"),
        required=False,
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = SiteSettings
        fields = ("family_name", "central_person")

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_view_password") or ""
        repeat = cleaned.get("repeat_view_password") or ""
        if not new and not repeat:
            return cleaned
        if new != repeat:
            self.add_error("repeat_view_password", ValidationError(_("The two passwords are different."), code="mismatch"))
        elif not new.strip():
            self.add_error(
                "new_view_password",
                ValidationError(_("The password cannot be only spaces."), code="blank"),
            )
        elif len(new) < PASSWORD_MIN_LENGTH:
            self.add_error(
                "new_view_password",
                ValidationError(_("The password needs at least 8 characters."), code="too_short"),
            )
        return cleaned

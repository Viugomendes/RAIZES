"""The admin panel at /painel/: entered with e-mail and password.

Wrong logins share the attempt limit of the view password (access/ratelimit.py):
more than 10 from one address in 15 minutes and the form refuses, even the
right password, until the time is over.
"""
from django import forms
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.utils.translation import gettext_lazy as _

from . import ratelimit

SCOPE = "admin-login"
# Shorter than the year of a viewer: the panel can change everything.
STAFF_SESSION_AGE = 12 * 60 * 60


class EmailLoginForm(AdminAuthenticationForm):
    username = forms.CharField(
        label=_("E-mail"),
        max_length=254,
        widget=forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"}),
    )
    error_messages = {
        **AdminAuthenticationForm.error_messages,
        "invalid_login": _("Wrong e-mail or password. Check them and try again."),
        "blocked": _("Too many wrong attempts. Wait 15 minutes and try again."),
    }

    def clean(self):
        # Counted before the check, so parallel guesses cannot slip past the limit.
        if ratelimit.attempt(SCOPE, ratelimit.client_ip(self.request)):
            raise ValidationError(self.error_messages["blocked"], code="blocked")
        return super().clean()


class RaizesAdminSite(admin.AdminSite):
    login_form = EmailLoginForm
    login_template = "access/admin_login.html"

    def login(self, request, extra_context=None):
        response = super().login(request, extra_context)
        if request.method != "POST":
            return response
        if response.status_code == 302 and request.user.is_authenticated:
            ratelimit.clear(SCOPE, ratelimit.client_ip(request))
            # The session may come from the view password, which lasts a year.
            request.session.set_expiry(STAFF_SESSION_AGE)
        else:
            form = getattr(response, "context_data", {}).get("form")
            if form is not None and form.has_error(NON_FIELD_ERRORS, "blocked"):
                response.status_code = 429
        return response


site = RaizesAdminSite(name="admin")

# Accounts and roles: only the owner (a superuser) has these permissions.
site.register(User, UserAdmin)
site.register(Group, GroupAdmin)

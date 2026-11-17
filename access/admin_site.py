"""The admin panel at /painel/: entered with e-mail and password.

Logins have their own attempt limit ("admin-login" in access/ratelimit.py,
separate from the view password): more than 10 from one address in 15 minutes
and the form refuses, even the right password, until the time is over. A good
login does not reset the count, so no other account can reset it for a guesser.

The password reset sends at most 10 e-mails per address of the sender and one
per e-mail address every 15 minutes.
"""
import hashlib
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import views as auth_views
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, PasswordResetForm, UserChangeForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _

from . import ratelimit

SCOPE = "admin-login"
RESET_SCOPE = "password-reset"
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
            # The session may come from the view password, which lasts a year.
            request.session.set_expiry(STAFF_SESSION_AGE)
        else:
            form = getattr(response, "context_data", {}).get("form")
            if form is not None and form.has_error(NON_FIELD_ERRORS, "blocked"):
                response.status_code = 429
        return response


site = RaizesAdminSite(name="admin")


class PanelPasswordResetForm(PasswordResetForm):
    """Only panel accounts get the e-mail: another account cannot use the panel."""

    def get_users(self, email):
        return (user for user in super().get_users(email) if user.is_staff)


class PasswordResetView(auth_views.PasswordResetView):
    """Django's reset; over a limit it shows the same "sent" page and sends nothing."""

    form_class = PanelPasswordResetForm

    def form_valid(self, form):
        email = form.cleaned_data["email"].strip().lower()
        address_key = "reset-sent:" + hashlib.sha256(email.encode()).hexdigest()
        if ratelimit.attempt(
            RESET_SCOPE, ratelimit.client_ip(self.request)
        ) or not ratelimit.first_time(address_key):
            return HttpResponseRedirect(self.get_success_url())
        if not settings.RAIZES_PUBLIC_URL:
            return super().form_valid(form)
        # Behind a tunnel the request is plain http to localhost: the link must
        # point at the address the family opens.
        public = urlsplit(settings.RAIZES_PUBLIC_URL)
        form.save(
            domain_override=public.netloc,
            use_https=public.scheme == "https",
            token_generator=self.token_generator,
            from_email=self.from_email,
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            request=self.request,
            html_email_template_name=self.html_email_template_name,
            extra_email_context=self.extra_email_context,
        )
        return HttpResponseRedirect(self.get_success_url())


class UniqueEmailMixin:
    """Every account needs its own e-mail: it is what logs in to the panel."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True

    def clean_email(self):
        email = self.cleaned_data["email"].strip()
        others = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if others.exists():
            raise ValidationError(_("Another account already uses this e-mail."), code="unique")
        return email


class AccountCreationForm(UniqueEmailMixin, AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        fields = ("username", "email")


class AccountChangeForm(UniqueEmailMixin, UserChangeForm):
    pass


class AccountAdmin(UserAdmin):
    add_form = AccountCreationForm
    form = AccountChangeForm
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "usable_password", "password1", "password2"),
            },
        ),
    )


# Accounts and roles: only the owner (a superuser) has these permissions.
site.register(User, AccountAdmin)
site.register(Group, GroupAdmin)

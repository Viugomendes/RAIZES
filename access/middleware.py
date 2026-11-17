"""The view password: every page, photo and data file of the family needs it.

The admin panel, the password page itself, the static files and robots.txt
are public. Logged-in staff and the export (which asks Django for each page
from inside the program) pass without a password.
"""
import datetime
import threading
import uuid
from contextlib import contextmanager
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import SiteSettings, ViewerDevice

# The session key holding the id of this browser's ViewerDevice.
SESSION_KEY = "raizes_device"
TOUCH_EVERY = datetime.timedelta(seconds=60)
LANGUAGE_COOKIE_AGE = 365 * 24 * 60 * 60

# Thread-local, so an export never opens the site to requests served by other threads.
_state = threading.local()


@contextmanager
def exporting():
    """Inside this block, the requests made by this thread are not gated."""
    previous = getattr(_state, "exporting", False)
    _state.exporting = True
    try:
        yield
    finally:
        _state.exporting = previous


def _public_prefixes() -> tuple[str, ...]:
    return (
        reverse("access:enter"),
        reverse("access:leave"),
        reverse("admin:index"),
        settings.STATIC_URL,
        "/robots.txt",
        "/favicon.ico",
    )


def current_device(request, site: SiteSettings) -> ViewerDevice | None:
    """The device of this session, if it is still allowed in."""
    device_id = request.session.get(SESSION_KEY)
    if device_id is None:
        return None
    device = ViewerDevice.objects.filter(pk=device_id).first() if is_device_id(device_id) else None
    if device is None or not device.is_valid(site):
        request.session.pop(SESSION_KEY, None)
        return None
    return device


def is_device_id(value) -> bool:
    """A malformed value in the session counts as no device, never an error."""
    try:
        uuid.UUID(str(value))
    except ValueError:
        return False
    return True


def enter_url(next_path: str) -> str:
    return f"{reverse('access:enter')}?{urlencode({'next': next_path})}"


def site_closed(request):
    """No view password yet: send to the panel with a notice."""
    messages.warning(
        request, _("The family site is closed until a view password is set in the panel.")
    )
    return redirect(reverse("admin:index"))


class ViewPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            not settings.RAIZES_VIEW_GATE
            or getattr(_state, "exporting", False)
            or request.path_info.startswith(_public_prefixes())
        ):
            return self.get_response(request)
        user = request.user
        if user.is_active and user.is_staff:
            return private(self.get_response(request))
        site = SiteSettings.get()
        if not site.has_view_password:
            return site_closed(request)
        device = current_device(request, site)
        if device is None:
            return redirect(enter_url(request.get_full_path()))
        now = timezone.now()
        if now - device.last_seen > TOUCH_EVERY:
            ViewerDevice.objects.filter(pk=device.pk).update(last_seen=now)
        return private(self.get_response(request))


def private(response):
    """What passed the gate: no cache on the way (tunnel, proxy) may keep a copy.

    The same value as the Cloudflare function (functions/_middleware.js).
    """
    response.headers["Cache-Control"] = "private, no-store"
    return response


class LanguageCookieMiddleware:
    """Remember the language of the last page seen, so "/" opens in it."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        language = translation.get_language_from_path(request.path_info)
        if (
            language
            and response.status_code == 200
            and request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) != language
        ):
            set_language_cookie(response, language)
        return response


def set_language_cookie(response, language: str) -> None:
    response.set_cookie(
        settings.LANGUAGE_COOKIE_NAME,
        language,
        max_age=LANGUAGE_COOKIE_AGE,
        samesite="Lax",
        secure=settings.LANGUAGE_COOKIE_SECURE,
    )

"""The password page (/entrar/), leaving (/sair/) and robots.txt."""
import re
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponse
from django.middleware.csrf import rotate_token
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from . import ratelimit
from .devices import describe_browser, ip_prefix
from .middleware import (
    SESSION_KEY,
    current_device,
    is_device_id,
    set_language_cookie,
    site_closed,
)
from .models import SiteSettings, ViewerDevice

# One "/" and then visible ASCII; never "//" or "/\" (another site for the browser).
_SAFE_NEXT = re.compile(r"/(?![/\\])[\x21-\x7e]*")
NAME_MAX = 80
VIEWER_SESSION_AGE = 365 * 24 * 60 * 60
SCOPE = "enter"


def safe_next(value: str) -> str:
    return value if _SAFE_NEXT.fullmatch(value or "") else "/"


def _client_ip(request) -> str:
    # Only REMOTE_ADDR: X-Forwarded-For can be typed by anybody.
    return request.META.get("REMOTE_ADDR", "")


def enter(request):
    site = SiteSettings.get()
    if not site.has_view_password:
        return site_closed(request)

    chosen = request.GET.get("lang")
    if chosen not in dict(settings.LANGUAGES):
        chosen = None
    if chosen:
        translation.activate(chosen)
        request.LANGUAGE_CODE = chosen

    next_url = safe_next(request.POST.get("next") or request.GET.get("next", ""))
    name = request.POST.get("name", "").strip()[:NAME_MAX]
    error = ""
    status = 200

    if request.method == "POST":
        ip = _client_ip(request)
        # Counted before the check, so parallel guesses cannot slip past the limit.
        if ratelimit.attempt(SCOPE, ip):
            error = _("Too many wrong attempts. Wait 15 minutes and try again.")
            status = 429
        elif site.check_view_password(request.POST.get("password", "")):
            ratelimit.clear(SCOPE, ip)
            device = ViewerDevice.objects.create(
                name=name,
                browser=describe_browser(request.META.get("HTTP_USER_AGENT", ""))[:80],
                ip_prefix=ip_prefix(ip),
                password_version=site.password_version,
            )
            # A new session key, so a key known before the password is useless.
            request.session.cycle_key()
            rotate_token(request)
            request.session[SESSION_KEY] = str(device.pk)
            # A viewer stays in for a year; a staff session keeps its own, shorter life.
            if not request.user.is_staff:
                request.session.set_expiry(VIEWER_SESSION_AGE)
            return redirect(next_url)
        else:
            error = _("Wrong password. Check it and try again.")

    current = translation.get_language()
    languages = [
        {
            "code": code,
            "name": language_name,
            "url": f"{reverse('access:enter')}?{urlencode({'lang': code, 'next': next_url})}",
            "is_current": code == current,
        }
        for code, language_name in settings.LANGUAGES
    ]
    response = render(
        request,
        "access/enter.html",
        {
            "next": next_url,
            "name": name,
            "error": error,
            "enter_languages": languages,
            "already_in": current_device(request, site) is not None,
        },
        status=status,
    )
    if chosen:
        set_language_cookie(response, chosen)
    return response


@require_POST
def leave(request):
    device_id = request.session.pop(SESSION_KEY, None)
    if is_device_id(device_id):
        ViewerDevice.objects.filter(pk=device_id).update(revoked=True)
    return redirect("access:enter")


def robots(request):
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")

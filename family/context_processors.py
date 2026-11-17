"""Values that every page template needs."""
from django.conf import settings
from django.urls import translate_url
from django.utils.translation import get_language

from access.config import family_name
from access.middleware import SESSION_KEY


def site(request):
    """Family name, demo flag and the links of the language selector."""
    current = get_language()
    languages = [
        {
            "code": code,
            "name": name,
            "url": translate_url(request.path, code),
            "is_current": code == current,
        }
        for code, name in settings.LANGUAGES
    ]
    return {
        "family_name": family_name(),
        # A viewer's own device (never staff, never the static export): can leave.
        "can_leave": bool(
            hasattr(request, "session")
            and request.session.get(SESSION_KEY)
            and not request.user.is_staff
        ),
        "is_demo": settings.RAIZES_DATASET == "demo",
        "site_languages": languages,
    }

"""Values that every page template needs."""
from django.conf import settings
from django.urls import translate_url
from django.utils import translation
from django.utils.translation import get_language, gettext

from access.config import family_name
from access.middleware import SESSION_KEY

from .strings import header_strings


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
    # The header shows one flag, the current one; it leads to the next language.
    position = next((i for i, language in enumerate(languages) if language["is_current"]), 0)
    next_language = dict(languages[(position + 1) % len(languages)])
    # In the language it leads to: whoever wants that language can read it.
    with translation.override(next_language["code"]):
        next_language["label"] = gettext("Change language to %(language)s") % {
            "language": next_language["name"]
        }
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
        "current_language": languages[position],
        "next_language": next_language,
        "header_strings": header_strings(),
    }

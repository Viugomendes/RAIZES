"""Values that every page template needs."""
from django.conf import settings
from django.urls import translate_url
from django.utils.translation import get_language

from access.config import family_name


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
        "is_demo": settings.RAIZES_DATASET == "demo",
        "site_languages": languages,
    }

"""Settings of the Raízes project.

Until version 1.0 Django runs only on the owner's computer: the admin panel is
used to fill in the data, and the site is exported as static pages.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

from .env import get_or_create_secret_key, load_env_file, parse_list

BASE_DIR = Path(__file__).resolve().parent.parent

# Local configuration and secrets live in `.env`, which Git ignores.
ENV_FILE = BASE_DIR / ".env"
load_env_file(ENV_FILE)

SECRET_KEY = get_or_create_secret_key(ENV_FILE)

# Django only ever runs on this computer, so debug mode is the default.
DEBUG = os.environ.get("RAIZES_DEBUG", "true").lower() in ("1", "true", "yes")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# ---------------------------------------------------------------------------
# Which family is loaded
# ---------------------------------------------------------------------------
# "demo": the invented family, kept in demo/ (safe to show to anyone).
# "real": the real family, kept in data/ (private, never goes to Git).
RAIZES_DATASET = os.environ.get("RAIZES_DATASET", "demo").strip().lower()
if RAIZES_DATASET not in ("demo", "real"):
    raise ImproperlyConfigured(
        "RAIZES_DATASET must be 'demo' or 'real' (check the .env file)."
    )

# The invented family's central person (must match demo/family.toml).
DEMO_CENTRAL_PERSON = "lia-carvalho-1996"
DEMO_FAMILY_NAME = "Família Carvalho Figueira"

if RAIZES_DATASET == "real":
    DATA_DIR = BASE_DIR / "data"
    DATABASE_FILE = DATA_DIR / "raizes.sqlite3"
    _default_central_person = ""
    _default_family_name = ""
else:
    DATA_DIR = BASE_DIR / "demo"
    DATABASE_FILE = DATA_DIR / "demo.sqlite3"
    _default_central_person = DEMO_CENTRAL_PERSON
    _default_family_name = DEMO_FAMILY_NAME
DATA_DIR.mkdir(exist_ok=True)

# The tree is organised from this person outwards (identifier of a Person).
RAIZES_CENTRAL_PERSON = (
    os.environ.get("RAIZES_CENTRAL_PERSON", "").strip() or _default_central_person
)
# Shown in the header of every page.
RAIZES_FAMILY_NAME = (
    os.environ.get("RAIZES_FAMILY_NAME", "").strip() or _default_family_name
)
# Where the static site is written by `python manage.py export_site`.
RAIZES_EXPORT_DIR = BASE_DIR / "dist"

# Sections of the person page that this family does not want to show:
# tastes, childhood, work, love, origins, memories, legacy, remembrance, gallery.
RAIZES_HIDDEN_SECTIONS = set(parse_list(os.environ.get("RAIZES_HIDDEN_SECTIONS", "")))

# The family pages, photos and data need the view password (set in the panel).
# The tests switch it off (config/test_runner.py); only the tests of the gate turn it on.
RAIZES_VIEW_GATE = os.environ.get("RAIZES_VIEW_GATE", "true").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_distill",
    "family",
    "access",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # After the login and the messages: staff pass, and the "site closed" notice is shown.
    "access.middleware.ViewPasswordMiddleware",
    "access.middleware.LanguageCookieMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "family.context_processors.site",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATABASE_FILE,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Sessions keep Django's default life (2 weeks). A device that typed the view
# password is given a year in access/views.py.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

TEST_RUNNER = "config.test_runner.RaizesTestRunner"

# ---------------------------------------------------------------------------
# Languages
# ---------------------------------------------------------------------------
# The code is written in English; the interface is translated in locale/.
LANGUAGES = [
    ("pt-br", "Português"),
    ("es", "Español"),
]
# The language the site opens in (the other one is a flag away).
LANGUAGE_CODE = os.environ.get("RAIZES_LANGUAGE", "pt-br").strip().lower() or "pt-br"
if LANGUAGE_CODE not in dict(LANGUAGES):
    raise ImproperlyConfigured(
        "RAIZES_LANGUAGE in .env must be one of: " + ", ".join(dict(LANGUAGES))
    )
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_I18N = True
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = True

# ---------------------------------------------------------------------------
# Files
# ---------------------------------------------------------------------------
# CSS, JavaScript and icons of the site. Everything is inside the project:
# no library is loaded from another server.
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / ".build" / "static"

# Photos uploaded through the admin panel (the originals: never exported).
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
# Smaller copies of the photos, made once and reused.
RAIZES_CACHE_DIR = DATA_DIR / "cache"
# When each person, photo and recipe was first exported ("new on the site").
RAIZES_HISTORY_FILE = DATA_DIR / "export-history.json"

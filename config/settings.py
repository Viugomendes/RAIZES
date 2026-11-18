"""Settings of the Raízes project.

The admin panel is used to fill in the data. The site is served by
`python manage.py servir` (on this computer, the home network, a tunnel or a
server: see "Onde hospedar" in the README) or exported as static pages.
Everything that changes between places is read from `.env`.
"""
import os
from pathlib import Path
from urllib.parse import urlsplit

from django.core.exceptions import ImproperlyConfigured

from .env import get_or_create_secret_key, load_env_file, parse_bool, parse_list

BASE_DIR = Path(__file__).resolve().parent.parent

# Local configuration and secrets live in `.env`, which Git ignores.
ENV_FILE = BASE_DIR / ".env"
load_env_file(ENV_FILE)

SECRET_KEY = get_or_create_secret_key(ENV_FILE)

# ---------------------------------------------------------------------------
# Where the site is served (see "Onde hospedar" in the README)
# ---------------------------------------------------------------------------
# The address the family opens, for example https://familia.example.org
# Empty: the site is only used on this computer or on the home network.
RAIZES_PUBLIC_URL = os.environ.get("RAIZES_PUBLIC_URL", "").strip().rstrip("/").lower()
_public = urlsplit(RAIZES_PUBLIC_URL)
if RAIZES_PUBLIC_URL and (
    _public.scheme not in ("http", "https")
    or not _public.hostname
    or "@" in _public.netloc
    or _public.path
    or _public.query
    or _public.fragment
):
    raise ImproperlyConfigured(
        "RAIZES_PUBLIC_URL must look like https://familia.example.org (check the .env file)."
    )
RAIZES_PUBLIC_HTTPS = _public.scheme == "https"

# The names this site answers to. Never "*": a request for another name is refused.
RAIZES_EXTRA_HOSTS = parse_list(os.environ.get("RAIZES_EXTRA_HOSTS", ""))
if "*" in RAIZES_EXTRA_HOSTS:
    raise ImproperlyConfigured("RAIZES_EXTRA_HOSTS cannot be '*': write each name.")
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]
CSRF_TRUSTED_ORIGINS = []
if RAIZES_PUBLIC_URL:
    # An IPv6 address is written between brackets, as in the Host header.
    ALLOWED_HOSTS.append(f"[{_public.hostname}]" if ":" in _public.hostname else _public.hostname)
    CSRF_TRUSTED_ORIGINS.append(f"{_public.scheme}://{_public.netloc}")
ALLOWED_HOSTS += [host for host in RAIZES_EXTRA_HOSTS if host not in ALLOWED_HOSTS]

# Behind a tunnel or a proxy every visit comes from the same local address; this
# header then carries the visitor's address (used by the attempt limits).
#   empty (default): no proxy, the address of the connection is used;
#   CF-Connecting-IP: Cloudflare Tunnel;
#   X-Forwarded-For: a proxy on the same computer (Caddy); its last entry is used.
_proxy_headers = {"cf-connecting-ip": "CF-Connecting-IP", "x-forwarded-for": "X-Forwarded-For"}
_proxy = os.environ.get("RAIZES_PROXY_HEADER", "").strip()
if _proxy and _proxy.lower() not in _proxy_headers:
    raise ImproperlyConfigured(
        "RAIZES_PROXY_HEADER must be empty, CF-Connecting-IP or X-Forwarded-For."
    )
RAIZES_PROXY_HEADER = _proxy_headers.get(_proxy.lower(), "")
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if RAIZES_PROXY_HEADER else None

# Debug mode shows code, settings and folders when something goes wrong. It is
# the default only on this computer, and refused when the site is published.
_published = bool(RAIZES_PUBLIC_URL or RAIZES_PROXY_HEADER)
_debug = os.environ.get("RAIZES_DEBUG", "").strip()
DEBUG = parse_bool(_debug, "RAIZES_DEBUG") if _debug else not _published
if DEBUG and _published:
    raise ImproperlyConfigured(
        "RAIZES_DEBUG cannot be true with RAIZES_PUBLIC_URL or RAIZES_PROXY_HEADER: "
        "the debug pages would be open to the internet. Set RAIZES_DEBUG=false in .env."
    )

# With an https address the cookies only travel over https, and the browser is told
# to always use https (HSTS, one year). The tunnel or the proxy sends http to https.
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = LANGUAGE_COOKIE_SECURE = RAIZES_PUBLIC_HTTPS
SECURE_HSTS_SECONDS = 31536000 if RAIZES_PUBLIC_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_SSL_REDIRECT = False

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
RAIZES_VIEW_GATE = parse_bool(os.environ.get("RAIZES_VIEW_GATE"), "RAIZES_VIEW_GATE")
if not RAIZES_VIEW_GATE and RAIZES_PUBLIC_URL:
    raise ImproperlyConfigured(
        "RAIZES_VIEW_GATE cannot be false with RAIZES_PUBLIC_URL: the family site would "
        "be open to anybody. Set RAIZES_VIEW_GATE=true in .env."
    )


# ---------------------------------------------------------------------------
# Django
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    # Before the admin: its templates/admin/base_site.html styles every panel page.
    "access",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_distill",
    "family",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # The same Content-Security-Policy and headers as the Cloudflare function.
    # Before WhiteNoise, which answers static files by itself: they get them too.
    "access.security.SecurityHeadersMiddleware",
    # CSS, JavaScript and icons (see WHITENOISE_USE_FINDERS below).
    "whitenoise.middleware.WhiteNoiseMiddleware",
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

# The attempt limits (access/ratelimit.py) have a cache of their own: filling the
# default one (300 entries) must never make Django forget a guesser's counter.
CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "ratelimit": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "raizes-ratelimit",
        "OPTIONS": {"MAX_ENTRIES": 100000},
    },
}

# The panel (/painel/) is entered with e-mail and password, staff accounts only.
AUTHENTICATION_BACKENDS = ["access.backends.EmailBackend"]
LOGIN_URL = "admin:login"

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
# WhiteNoise also finds the files where they are (static/ and each app): the CSS
# loads under runserver and servir even without debug and before collectstatic.
WHITENOISE_USE_FINDERS = True

# Photos uploaded through the admin panel (the originals: never exported).
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
# Smaller copies of the photos, made once and reused.
RAIZES_CACHE_DIR = DATA_DIR / "cache"
# When each person, photo and recipe was first exported ("new on the site").
RAIZES_HISTORY_FILE = DATA_DIR / "export-history.json"
# Where `python manage.py backup` writes its zip files (Git ignores it).
RAIZES_BACKUP_DIR = BASE_DIR / "backups"

# ---------------------------------------------------------------------------
# E-mail (the password of the panel is sent by e-mail; see the README)
# ---------------------------------------------------------------------------
# Without RAIZES_EMAIL_HOST nothing is sent: each e-mail is written as a file in
# DATA_DIR/emails, and `instalar` shows the panel password on the screen instead.
EMAIL_HOST = os.environ.get("RAIZES_EMAIL_HOST", "").strip()
RAIZES_EMAIL_CONFIGURED = bool(EMAIL_HOST)
try:
    EMAIL_PORT = int(os.environ.get("RAIZES_EMAIL_PORT", "").strip() or 587)
except ValueError:
    raise ImproperlyConfigured(
        "RAIZES_EMAIL_PORT must be a number, like 587 (check the .env file)."
    ) from None
EMAIL_HOST_USER = os.environ.get("RAIZES_EMAIL_USER", "").strip()
EMAIL_HOST_PASSWORD = os.environ.get("RAIZES_EMAIL_PASSWORD", "")
# Always encrypted: port 465 starts with TLS, any other port switches to it (STARTTLS).
EMAIL_USE_SSL = EMAIL_PORT == 465
EMAIL_USE_TLS = not EMAIL_USE_SSL
DEFAULT_FROM_EMAIL = (
    os.environ.get("RAIZES_EMAIL_FROM", "").strip() or EMAIL_HOST_USER or "raizes@localhost"
)
EMAIL_TIMEOUT = 15
if RAIZES_EMAIL_CONFIGURED:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.filebased.EmailBackend"
    EMAIL_FILE_PATH = DATA_DIR / "emails"

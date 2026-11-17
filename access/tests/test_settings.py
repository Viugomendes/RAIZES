"""Production settings: public address, HTTPS, e-mail, proxies and static files.

The settings are built in a separate Python process with the given environment,
so nothing changes in the settings of the running tests.
"""
import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.core.handlers.wsgi import WSGIHandler
from django.core.management import call_command
from django.test import RequestFactory, SimpleTestCase, TransactionTestCase, override_settings

from access.management.commands.servir import waitress_options
from access.models import SiteSettings
from access.ratelimit import client_ip

BASE_DIR = Path(settings.BASE_DIR)

# Every name read from .env: set empty here, so the developer's own .env never counts.
ENV_NAMES = (
    "RAIZES_DEBUG",
    "RAIZES_PUBLIC_URL",
    "RAIZES_EXTRA_HOSTS",
    "RAIZES_PROXY_HEADER",
    "RAIZES_EMAIL_HOST",
    "RAIZES_EMAIL_PORT",
    "RAIZES_EMAIL_USER",
    "RAIZES_EMAIL_PASSWORD",
    "RAIZES_EMAIL_FROM",
    "RAIZES_CENTRAL_PERSON",
    "RAIZES_FAMILY_NAME",
    "RAIZES_LANGUAGE",
    "RAIZES_HIDDEN_SECTIONS",
    "RAIZES_VIEW_GATE",
)
READ = (
    "DEBUG",
    "ALLOWED_HOSTS",
    "CSRF_TRUSTED_ORIGINS",
    "SESSION_COOKIE_SECURE",
    "CSRF_COOKIE_SECURE",
    "LANGUAGE_COOKIE_SECURE",
    "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    "SECURE_HSTS_PRELOAD",
    "SECURE_SSL_REDIRECT",
    "SECURE_PROXY_SSL_HEADER",
    "RAIZES_PUBLIC_URL",
    "RAIZES_PROXY_HEADER",
    "RAIZES_EMAIL_CONFIGURED",
    "EMAIL_BACKEND",
    "EMAIL_FILE_PATH",
    "EMAIL_HOST",
    "EMAIL_PORT",
    "EMAIL_HOST_USER",
    "EMAIL_HOST_PASSWORD",
    "EMAIL_USE_TLS",
    "EMAIL_USE_SSL",
    "DEFAULT_FROM_EMAIL",
    "DATA_DIR",
)
SCRIPT = (
    "import json, sys\n"
    "import config.settings as s\n"
    "print(json.dumps({name: getattr(s, name, None) for name in sys.argv[1:]}, default=str))\n"
)


def build_settings(**values):
    """The settings made from these environment values: (settings, error text)."""
    env = {name: value for name, value in os.environ.items() if not name.startswith("RAIZES_")}
    env.update({name: "" for name in ENV_NAMES})
    env.update(RAIZES_SECRET_KEY="only-for-this-test", RAIZES_DATASET="demo")
    env.update(values)
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT, *READ],
        cwd=BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode:
        return None, result.stderr
    return json.loads(result.stdout), ""


class SettingsTests(SimpleTestCase):
    def build(self, **values):
        built, error = build_settings(**values)
        self.assertIsNotNone(built, error)
        return built

    def assertRefused(self, **values):
        built, error = build_settings(**values)
        self.assertIsNone(built)
        self.assertIn("ImproperlyConfigured", error)

    def test_public_https_url_turns_on_secure_cookies_and_hosts(self):
        built = self.build(RAIZES_PUBLIC_URL="https://Familia.Example.org/")

        self.assertFalse(built["DEBUG"])
        self.assertEqual(
            built["ALLOWED_HOSTS"], ["localhost", "127.0.0.1", "[::1]", "familia.example.org"]
        )
        self.assertEqual(built["CSRF_TRUSTED_ORIGINS"], ["https://familia.example.org"])
        self.assertEqual(built["RAIZES_PUBLIC_URL"], "https://familia.example.org")
        for name in ("SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "LANGUAGE_COOKIE_SECURE"):
            self.assertIs(built[name], True, name)
        self.assertEqual(built["SECURE_HSTS_SECONDS"], 31536000)
        self.assertIs(built["SECURE_HSTS_INCLUDE_SUBDOMAINS"], False)
        self.assertIs(built["SECURE_HSTS_PRELOAD"], False)
        # The tunnel or the proxy sends http to https, not Django.
        self.assertIs(built["SECURE_SSL_REDIRECT"], False)

    def test_public_http_url_allows_the_host_with_plain_cookies(self):
        built = self.build(RAIZES_PUBLIC_URL="http://raizes.casa:8000")

        self.assertIn("raizes.casa", built["ALLOWED_HOSTS"])
        self.assertEqual(built["CSRF_TRUSTED_ORIGINS"], ["http://raizes.casa:8000"])
        self.assertIs(built["SESSION_COOKIE_SECURE"], False)
        self.assertEqual(built["SECURE_HSTS_SECONDS"], 0)

    def test_without_public_url_debug_stays_local(self):
        built = self.build()

        self.assertTrue(built["DEBUG"])
        self.assertEqual(built["ALLOWED_HOSTS"], ["localhost", "127.0.0.1", "[::1]"])
        self.assertEqual(built["CSRF_TRUSTED_ORIGINS"], [])
        self.assertIs(built["SESSION_COOKIE_SECURE"], False)
        self.assertEqual(built["SECURE_HSTS_SECONDS"], 0)
        self.assertIsNone(built["SECURE_PROXY_SSL_HEADER"])

    def test_an_explicit_debug_value_wins_and_a_typo_is_refused(self):
        self.assertFalse(self.build(RAIZES_DEBUG="false")["DEBUG"])
        self.assertTrue(self.build(RAIZES_DEBUG="true")["DEBUG"])
        self.assertRefused(RAIZES_DEBUG="talvez")

    def test_debug_is_refused_on_a_public_address_or_behind_a_proxy(self):
        # The debug pages show code, settings and folders: never to the internet.
        self.assertRefused(RAIZES_PUBLIC_URL="https://a.example", RAIZES_DEBUG="true")
        self.assertRefused(RAIZES_PROXY_HEADER="CF-Connecting-IP", RAIZES_DEBUG="true")
        self.assertFalse(self.build(RAIZES_PROXY_HEADER="CF-Connecting-IP")["DEBUG"])

    def test_a_public_address_without_the_view_password_is_refused(self):
        self.assertRefused(RAIZES_PUBLIC_URL="https://a.example", RAIZES_VIEW_GATE="false")
        self.assertIsNotNone(build_settings(RAIZES_VIEW_GATE="false")[0])

    def test_extra_hosts_are_added_and_never_everything(self):
        built = self.build(RAIZES_EXTRA_HOSTS="raizes.local, 192.168.0.7")

        self.assertEqual(built["ALLOWED_HOSTS"][3:], ["raizes.local", "192.168.0.7"])
        self.assertRefused(RAIZES_EXTRA_HOSTS="*")

    def test_a_public_url_without_http_or_a_host_is_refused(self):
        for url in ("familia.example.org", "ftp://familia.example.org", "https://", "https://a.org/x"):
            with self.subTest(url=url):
                self.assertRefused(RAIZES_PUBLIC_URL=url)

    def test_without_smtp_e_mails_go_to_files(self):
        built = self.build()

        self.assertEqual(built["EMAIL_BACKEND"], "django.core.mail.backends.filebased.EmailBackend")
        self.assertEqual(Path(built["EMAIL_FILE_PATH"]), Path(built["DATA_DIR"]) / "emails")
        self.assertIs(built["RAIZES_EMAIL_CONFIGURED"], False)

    def test_with_smtp_the_smtp_backend_is_used(self):
        built = self.build(
            RAIZES_EMAIL_HOST="smtp.gmail.com",
            RAIZES_EMAIL_USER="familia@gmail.com",
            RAIZES_EMAIL_PASSWORD="abcd efgh ijkl mnop",
        )

        self.assertEqual(built["EMAIL_BACKEND"], "django.core.mail.backends.smtp.EmailBackend")
        self.assertIs(built["RAIZES_EMAIL_CONFIGURED"], True)
        self.assertEqual(built["EMAIL_HOST"], "smtp.gmail.com")
        self.assertEqual(built["EMAIL_PORT"], 587)
        self.assertEqual(built["EMAIL_HOST_USER"], "familia@gmail.com")
        self.assertEqual(built["EMAIL_HOST_PASSWORD"], "abcd efgh ijkl mnop")
        self.assertEqual((built["EMAIL_USE_TLS"], built["EMAIL_USE_SSL"]), (True, False))
        self.assertEqual(built["DEFAULT_FROM_EMAIL"], "familia@gmail.com")

        other = self.build(
            RAIZES_EMAIL_HOST="smtp.example.org", RAIZES_EMAIL_PORT="465",
            RAIZES_EMAIL_FROM="Raízes <raizes@example.org>",
        )
        self.assertEqual((other["EMAIL_USE_TLS"], other["EMAIL_USE_SSL"]), (False, True))
        self.assertEqual(other["DEFAULT_FROM_EMAIL"], "Raízes <raizes@example.org>")
        self.assertRefused(RAIZES_EMAIL_HOST="smtp.example.org", RAIZES_EMAIL_PORT="porta")

    def test_proxy_header_is_off_by_default_and_only_known_values_are_accepted(self):
        self.assertEqual(self.build()["RAIZES_PROXY_HEADER"], "")
        for value, expected in (("CF-Connecting-IP", "CF-Connecting-IP"), ("x-forwarded-for", "X-Forwarded-For")):
            with self.subTest(value=value):
                built = self.build(RAIZES_PROXY_HEADER=value)
                self.assertEqual(built["RAIZES_PROXY_HEADER"], expected)
                self.assertEqual(built["SECURE_PROXY_SSL_HEADER"], ["HTTP_X_FORWARDED_PROTO", "https"])
        self.assertRefused(RAIZES_PROXY_HEADER="X-Real-IP")

    def test_whitenoise_serves_static_files_after_the_security_headers(self):
        middleware = settings.MIDDLEWARE
        whitenoise = middleware.index("whitenoise.middleware.WhiteNoiseMiddleware")
        self.assertLess(middleware.index("django.middleware.security.SecurityMiddleware"), whitenoise)
        # WhiteNoise answers by itself: what comes later never sees the static files.
        self.assertLess(middleware.index("access.security.SecurityHeadersMiddleware"), whitenoise)


class EnvExampleTests(SimpleTestCase):
    def test_every_setting_read_from_env_is_explained_in_the_example(self):
        code = (BASE_DIR / "config" / "settings.py").read_text(encoding="utf-8")
        example = (BASE_DIR / ".env.example").read_text(encoding="utf-8")

        names = set(re.findall(r'"(RAIZES_[A-Z_]+)"', code)) - {"RAIZES_SECRET_KEY"}
        self.assertTrue(names)
        for name in sorted(names):
            self.assertRegex(example, rf"(?m)^{name}=", name)


class StaticFilesTests(SimpleTestCase):
    def test_static_file_is_served_without_debug(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        with override_settings(STATIC_ROOT=folder.name, DEBUG=False):
            call_command("collectstatic", interactive=False, verbosity=0)
            response = self.client.get("/static/css/site.css")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                b"".join(response.streaming_content),
                (BASE_DIR / "static" / "css" / "site.css").read_bytes(),
            )
            self.assertIn("Content-Security-Policy", response.headers)
            self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")


@override_settings(
    RAIZES_VIEW_GATE=True,
    SECURE_HSTS_SECONDS=31536000,
    SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
)
class BehindAProxyTests(TransactionTestCase):
    """The real waitress, as `servir` starts it, receiving visits from a local proxy."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        SiteSettings.get().set_view_password("bolo-de-fuba")

    def start(self):
        import waitress

        server = waitress.create_server(
            WSGIHandler(), host="127.0.0.1", port=0, threads=2, **waitress_options()
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.close)
        return server.effective_port

    def request(self, port, method, path, headers, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.msg, response.read().decode()
        finally:
            connection.close()

    def wrong_password(self, port, forwarded):
        """One wrong attempt at /entrar/, with the CSRF cookie and token of a real browser."""
        status, headers, html = self.request(port, "GET", "/entrar/", forwarded)
        self.assertEqual(status, 200, html[:300])
        cookie = re.search(r"csrftoken=([^;]+)", " ".join(headers.get_all("Set-Cookie")))[1]
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)[1]
        body = urlencode({"csrfmiddlewaretoken": token, "password": "errada", "next": "/"})
        status, _headers, _html = self.request(
            port, "POST", "/entrar/", {
                **forwarded,
                "Cookie": f"csrftoken={cookie}",
                "Content-Type": "application/x-www-form-urlencoded",
            }, body,
        )
        return status

    @override_settings(RAIZES_PROXY_HEADER="X-Forwarded-For")
    def test_each_forwarded_visitor_has_its_own_attempt_count(self):
        port = self.start()
        first = {"X-Forwarded-For": "6.6.6.6, 203.0.113.1"}
        for _attempt in range(10):
            self.assertEqual(self.wrong_password(port, first), 200)

        self.assertEqual(self.wrong_password(port, first), 429)
        # Another visitor (and a different spoofed first entry) is not locked out.
        self.assertEqual(self.wrong_password(port, {"X-Forwarded-For": "6.6.6.6, 203.0.113.2"}), 200)

    @override_settings(RAIZES_PROXY_HEADER="CF-Connecting-IP")
    def test_cloudflare_visitors_have_their_own_attempt_count(self):
        port = self.start()
        for _attempt in range(11):
            last = self.wrong_password(port, {"CF-Connecting-IP": "203.0.113.1"})

        self.assertEqual(last, 429)
        self.assertEqual(self.wrong_password(port, {"CF-Connecting-IP": "203.0.113.2"}), 200)

    def test_https_from_the_proxy_turns_on_hsts(self):
        for header in ("X-Forwarded-For", "CF-Connecting-IP"):
            with self.subTest(header=header), override_settings(RAIZES_PROXY_HEADER=header):
                port = self.start()
                _status, headers, _html = self.request(
                    port, "GET", "/robots.txt", {"X-Forwarded-Proto": "https"}
                )
                self.assertEqual(headers.get("Strict-Transport-Security"), "max-age=31536000")
                _status, headers, _html = self.request(port, "GET", "/robots.txt", {})
                self.assertNotIn("Strict-Transport-Security", headers)


class ClientIpTests(SimpleTestCase):
    def request(self, **meta):
        return RequestFactory().get("/", REMOTE_ADDR="127.0.0.1", **meta)

    def test_without_a_proxy_header_only_the_connection_counts(self):
        request = self.request(HTTP_CF_CONNECTING_IP="1.1.1.1", HTTP_X_FORWARDED_FOR="2.2.2.2")

        with override_settings(RAIZES_PROXY_HEADER=""):
            self.assertEqual(client_ip(request), "127.0.0.1")

    @override_settings(RAIZES_PROXY_HEADER="CF-Connecting-IP")
    def test_cloudflare_header_is_used_when_configured(self):
        request = self.request(HTTP_CF_CONNECTING_IP=" 203.0.113.9 ", HTTP_X_FORWARDED_FOR="2.2.2.2")

        self.assertEqual(client_ip(request), "203.0.113.9")
        self.assertEqual(client_ip(self.request()), "127.0.0.1")

    @override_settings(RAIZES_PROXY_HEADER="X-Forwarded-For")
    def test_forwarded_for_uses_the_last_entry_added_by_the_proxy(self):
        # The first entries come from the visitor and can be anything.
        spoofed = self.request(HTTP_X_FORWARDED_FOR="6.6.6.6, 7.7.7.7, 198.51.100.4")

        self.assertEqual(client_ip(spoofed), "198.51.100.4")
        self.assertEqual(client_ip(self.request(HTTP_X_FORWARDED_FOR="198.51.100.5")), "198.51.100.5")

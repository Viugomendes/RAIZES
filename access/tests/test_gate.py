"""The view password: nobody sees the family site without it."""
import datetime
import tempfile
import time
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.cache import cache, caches
from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from access import ratelimit
from access.middleware import SESSION_KEY
from access.models import SiteSettings, ViewerDevice
from access.tests import clear_caches
from family.export import export_site
from family.models import Clip
from family.tests.base import DemoFamilyTestCase
from family.tests.test_images import save_image

PASSWORD = "bolo-de-fuba"
ANDROID_CHROME = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)


def next_of(response) -> str:
    """The `next` of a redirect to the password page."""
    parts = urlsplit(response["Location"])
    assert parts.path == "/entrar/", response["Location"]
    return parse_qs(parts.query)["next"][0]


@override_settings(RAIZES_VIEW_GATE=True)
class GateTests(TestCase):
    def setUp(self):
        clear_caches()
        self.addCleanup(clear_caches)
        self.site = SiteSettings.get()
        self.site.set_view_password(PASSWORD)

    def enter(self, password=PASSWORD, name="", next_url="/pt-br/", **extra):
        return self.client.post(
            "/entrar/", {"name": name, "password": password, "next": next_url}, **extra
        )

    def test_pages_photos_and_data_need_the_password(self):
        for path in (
            "/pt-br/",
            "/pt-br/tree/",
            "/es/search/",
            "/data/family.js",
            "/media/v/480/photos/avo.jpg.jpg",
            "/media/clips/conversa.mp3",
        ):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(next_of(response), path)

    def test_right_password_opens_the_site_for_a_year(self):
        response = self.enter(
            name="Vó Dalva", next_url="/pt-br/tree/",
            HTTP_USER_AGENT=ANDROID_CHROME, REMOTE_ADDR="192.168.1.37",
        )

        self.assertRedirects(response, "/pt-br/tree/", fetch_redirect_response=False)
        self.assertGreaterEqual(
            self.client.session.get_expiry_age(), datetime.timedelta(days=364).total_seconds()
        )
        device = ViewerDevice.objects.get()
        self.assertEqual(device.name, "Vó Dalva")
        self.assertEqual(device.browser, "Chrome · Android")
        self.assertEqual(device.ip_prefix, "192.168.1.x")
        self.assertEqual(device.password_version, self.site.password_version)
        self.assertEqual(self.client.session[SESSION_KEY], str(device.pk))
        self.assertEqual(self.client.get("/pt-br/").status_code, 200)
        self.assertEqual(self.client.get("/data/family.js").status_code, 200)

    def test_name_is_optional_and_cut_to_80_letters(self):
        self.enter(name="  " + "a" * 100 + "  ")
        self.assertEqual(ViewerDevice.objects.get().name, "a" * 80)

    def test_raw_password_is_never_stored(self):
        self.enter(name="Vó Dalva")
        device = ViewerDevice.objects.get()
        for value in (device.name, device.browser, device.ip_prefix):
            self.assertNotIn(PASSWORD, value)
        self.assertNotIn(PASSWORD, str(dict(self.client.session)))

    def test_wrong_password_shows_an_error_in_the_page_language(self):
        response = self.enter(password="errada", HTTP_ACCEPT_LANGUAGE="es")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Contraseña equivocada")
        self.assertFalse(ViewerDevice.objects.exists())
        self.assertNotIn(SESSION_KEY, self.client.session)

        response = self.enter(password="errada", HTTP_ACCEPT_LANGUAGE="pt-br")
        self.assertContains(response, "Senha errada")

    def test_ten_wrong_attempts_block_for_a_while(self):
        for _attempt in range(10):
            self.assertEqual(self.enter(password="errada").status_code, 200)

        response = self.enter()

        self.assertEqual(response.status_code, 429)
        self.assertFalse(ViewerDevice.objects.exists())

    def test_attempts_are_counted_before_the_password_is_checked(self):
        for _attempt in range(10):
            self.enter(password="errada")

        # A right password while blocked is refused, counted, and does not reset the block.
        self.assertEqual(self.enter().status_code, 429)
        self.assertEqual(caches["ratelimit"].get(ratelimit._key("enter", "127.0.0.1")), 11)
        self.assertEqual(self.enter().status_code, 429)
        self.assertEqual(caches["ratelimit"].get(ratelimit._key("enter", "127.0.0.1")), 12)
        self.assertFalse(ViewerDevice.objects.exists())

    def test_ipv4_mapped_addresses_count_as_their_ipv4_address(self):
        for _attempt in range(10):
            self.enter(password="errada", REMOTE_ADDR="::ffff:1.2.3.4")

        self.assertEqual(self.enter(REMOTE_ADDR="1.2.3.4").status_code, 429)
        self.assertEqual(self.enter(REMOTE_ADDR="::ffff:9.9.9.9").status_code, 302)

    def test_the_block_lifts_after_15_minutes(self):
        for _attempt in range(11):
            self.enter(password="errada")
        self.assertEqual(self.enter().status_code, 429)

        # LocMemCache reads the clock through time.time(): move it 16 minutes on.
        later = time.time() + 16 * 60
        with mock.patch("django.core.cache.backends.locmem.time.time", return_value=later):
            response = self.enter()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(ViewerDevice.objects.exists())

    def test_right_password_clears_the_count(self):
        for _attempt in range(9):
            self.enter(password="errada")
        self.enter()
        for _attempt in range(9):
            self.enter(password="errada")

        self.assertEqual(self.enter().status_code, 302)

    def test_ipv6_addresses_are_grouped_by_their_64_prefix(self):
        for number in range(10):
            self.enter(password="errada", REMOTE_ADDR=f"2001:db8:1:2::{number + 1}")

        self.assertEqual(self.enter(REMOTE_ADDR="2001:db8:1:2:ffff::9").status_code, 429)
        self.assertEqual(self.enter(REMOTE_ADDR="2001:db8:1:3::1").status_code, 302)

    def test_a_48_prefix_is_limited_to_100_attempts(self):
        for number in range(100):
            self.assertFalse(ratelimit.attempt("test", f"2001:db8:1:{number:x}::1"))

        self.assertTrue(ratelimit.attempt("test", "2001:db8:1:ffff::1"))
        self.assertFalse(ratelimit.attempt("test", "2001:db8:2::1"))

    def test_a_blocked_48_prefix_creates_no_new_counters(self):
        for number in range(101):
            ratelimit.attempt("test", f"2001:db8:1:{number:x}::1")

        self.assertTrue(ratelimit.attempt("test", "2001:db8:1:ffff::1"))
        counters = caches["ratelimit"]
        self.assertIsNone(counters.get(ratelimit._key("test", "2001:db8:1:ffff::1")))

    def test_filling_the_default_cache_never_resets_a_counter(self):
        for _attempt in range(10):
            self.enter(password="errada", REMOTE_ADDR="10.0.0.1")

        # LocMemCache keeps 300 entries by default and then forgets the oldest.
        for number in range(400):
            cache.set(f"filler-{number}", number)

        self.assertEqual(self.enter(REMOTE_ADDR="10.0.0.1").status_code, 429)

    def test_many_64_prefixes_never_reset_a_counter(self):
        for _attempt in range(10):
            self.enter(password="errada", REMOTE_ADDR="10.0.0.1")

        # Two /48 networks, 200 /64 each: every new counter is a new cache entry.
        for network in (1, 2):
            for number in range(200):
                ratelimit.attempt("enter", f"2001:db8:{network}:{number:x}::1")

        self.assertEqual(self.enter(REMOTE_ADDR="10.0.0.1").status_code, 429)

    def test_viewer_session_lasts_a_year_but_a_staff_session_does_not(self):
        year = datetime.timedelta(days=364).total_seconds()
        user = get_user_model().objects.create_user("dona", password="x", is_staff=True)
        self.client.force_login(user)
        self.assertLess(self.client.session.get_expiry_age(), year)

        viewer = self.client_class()
        viewer.post("/entrar/", {"password": PASSWORD, "next": "/"})
        self.assertGreaterEqual(viewer.session.get_expiry_age(), year)

    def test_malformed_device_in_the_session_means_no_device(self):
        session = self.client.session
        session[SESSION_KEY] = "not-a-uuid"
        session.save()

        self.assertEqual(next_of(self.client.get("/pt-br/")), "/pt-br/")

        session = self.client.session
        session[SESSION_KEY] = "not-a-uuid"
        session.save()
        response = self.client.post("/sair/")
        self.assertRedirects(response, "/entrar/?lang=pt-br", fetch_redirect_response=False)

    def test_attempts_are_counted_per_address(self):
        for _attempt in range(10):
            self.enter(password="errada", REMOTE_ADDR="10.0.0.1")

        response = self.enter(REMOTE_ADDR="10.0.0.2")

        self.assertEqual(response.status_code, 302)

    def test_next_never_leaves_the_site(self):
        for next_url in ("//evil.example", "https://evil.example", "/\\evil", "", "pt-br/"):
            with self.subTest(next_url=next_url):
                response = self.enter(next_url=next_url)
                self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_what_passed_the_gate_is_never_kept_by_a_cache(self):
        # A tunnel or proxy cache must never hand the family's data to a stranger.
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        media = Path(folder.name) / "media"
        override = override_settings(MEDIA_ROOT=media, RAIZES_CACHE_DIR=Path(folder.name) / "cache")
        override.enable()
        self.addCleanup(override.disable)
        save_image(media / "photos" / "avo.jpg")
        clip = media / "clips" / "conversa.mp3"
        clip.parent.mkdir(parents=True)
        clip.write_bytes(b"ID3 not really a song")
        Clip.objects.create(file="clips/conversa.mp3")
        self.enter()

        for path in ("/pt-br/", "/data/family.js", "/media/v/480/photos/avo.jpg.jpg", "/media/clips/conversa.mp3"):
            with self.subTest(path=path):
                response = self.client.get(path)
                response.close()  # files are streamed: let Windows delete the folder
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get("Cache-Control"), "private, no-store")

        staff = get_user_model().objects.create_user("dona", password="x", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/data/family.js")["Cache-Control"], "private, no-store")

    def test_the_gate_answers_are_never_kept_by_a_cache(self):
        # A kept redirect would send the family back to /entrar/ for minutes.
        redirect = self.client.get("/data/family.js")
        self.assertEqual(redirect.status_code, 302)
        self.assertEqual(redirect["Cache-Control"], "private, no-store")

        page = self.client.get("/entrar/")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page["Cache-Control"], "private, no-store")

        self.site.view_password_hash = ""
        self.site.save()
        for path in ("/pt-br/", "/entrar/"):
            with self.subTest(path=path):
                closed = self.client.get(path)
                self.assertEqual(closed.status_code, 302)
                self.assertEqual(closed["Cache-Control"], "private, no-store")

    def test_public_answers_are_not_marked_private(self):
        self.assertNotIn("Cache-Control", self.client.get("/robots.txt"))

    def test_next_is_kept_in_the_form(self):
        response = self.client.get("/entrar/?next=/pt-br/tree/")

        self.assertContains(response, 'name="next" value="/pt-br/tree/"')

    def test_revoked_device_is_sent_back_to_the_password_page(self):
        self.enter()
        ViewerDevice.objects.update(revoked=True)

        response = self.client.get("/pt-br/")

        self.assertEqual(next_of(response), "/pt-br/")

    def test_password_change_disconnects_everybody(self):
        self.enter()
        self.assertEqual(self.client.get("/pt-br/").status_code, 200)

        SiteSettings.get().set_view_password("pao-de-queijo")

        self.assertEqual(next_of(self.client.get("/pt-br/")), "/pt-br/")

    def test_last_seen_is_updated_at_most_once_a_minute(self):
        self.enter()
        long_ago = timezone.now() - datetime.timedelta(minutes=2)
        ViewerDevice.objects.update(last_seen=long_ago)

        with CaptureQueriesContext(connection) as queries:
            self.client.get("/pt-br/")
            self.client.get("/pt-br/tree/")

        writes = [
            query["sql"] for query in queries.captured_queries
            if query["sql"].startswith("UPDATE") and "access_viewerdevice" in query["sql"]
        ]
        self.assertEqual(len(writes), 1)
        self.assertGreater(ViewerDevice.objects.get().last_seen, long_ago)

    def test_logged_in_admin_sees_the_site(self):
        user = get_user_model().objects.create_user("dona", password="x", is_staff=True)
        self.client.force_login(user)

        self.assertEqual(self.client.get("/pt-br/").status_code, 200)
        self.assertFalse(ViewerDevice.objects.exists())

    def test_a_logged_in_account_that_is_not_staff_still_needs_the_password(self):
        user = get_user_model().objects.create_user("primo", password="x", is_staff=False)
        self.client.force_login(user)

        self.assertEqual(next_of(self.client.get("/pt-br/")), "/pt-br/")

    def test_staff_sees_the_site_even_while_it_is_closed(self):
        # The owner can look at the site before choosing the family password.
        self.site.view_password_hash = ""
        self.site.save()
        user = get_user_model().objects.create_user("dona", password="x", is_staff=True)
        self.client.force_login(user)

        response = self.client.get("/pt-br/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_without_a_view_password_the_site_is_closed(self):
        self.site.view_password_hash = ""
        self.site.save()

        for path in ("/pt-br/", "/entrar/"):
            with self.subTest(path=path):
                response = self.client.get(path, HTTP_ACCEPT_LANGUAGE="pt-br")
                self.assertRedirects(
                    response, reverse("admin:index"), fetch_redirect_response=False
                )
                notices = [str(message) for message in get_messages(response.wsgi_request)]
                self.assertTrue(any("senha" in notice for notice in notices), notices)

    def test_leave_disconnects_this_device(self):
        self.enter()

        response = self.client.post("/sair/")

        self.assertRedirects(response, "/entrar/?lang=pt-br", fetch_redirect_response=False)
        self.assertTrue(ViewerDevice.objects.get().revoked)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertEqual(next_of(self.client.get("/pt-br/")), "/pt-br/")

    def test_leave_keeps_the_language_of_the_page(self):
        for posted, expected in (("es", "es"), ("pt-br", "pt-br"), ("xx", "es")):
            with self.subTest(posted=posted):
                self.enter()
                response = self.client.post(
                    "/sair/", {"lang": posted}, HTTP_ACCEPT_LANGUAGE="es"
                )
                self.assertRedirects(
                    response, f"/entrar/?lang={expected}", fetch_redirect_response=False
                )

    def test_leave_needs_a_post(self):
        self.enter()

        self.assertEqual(self.client.get("/sair/").status_code, 405)
        self.assertFalse(ViewerDevice.objects.get().revoked)

    def test_password_form_is_protected_against_forged_requests(self):
        client = self.client_class(enforce_csrf_checks=True)

        response = client.post("/entrar/", {"password": PASSWORD, "next": "/"})

        self.assertEqual(response.status_code, 403)
        self.assertFalse(ViewerDevice.objects.exists())

    def test_static_files_and_robots_are_public(self):
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        self.assertIn("Disallow: /", robots.content.decode())

        self.assertEqual(self.client.get("/entrar/").status_code, 200)
        # The panel asks for its own login, not for the view password.
        admin = self.client.get(reverse("admin:index"))
        self.assertEqual(admin.status_code, 302)
        self.assertTrue(admin["Location"].startswith(reverse("admin:login")))
        # No favicon.ico exists: a plain 404, not the password page.
        self.assertEqual(self.client.get("/favicon.ico").status_code, 404)

        with override_settings(ROOT_URLCONF="access.tests.urls_with_static"):
            static = self.client.get("/static/css/site.css")
            self.assertEqual(static.status_code, 200)
            self.assertIn(b":root", b"".join(static.streaming_content))

    def test_password_page_follows_the_browser_language_and_has_the_flags(self):
        response = self.client.get("/entrar/?next=/es/tree/", HTTP_ACCEPT_LANGUAGE="es")

        self.assertContains(response, "Contraseña")
        self.assertContains(response, 'lang="es"')
        self.assertContains(response, 'href="/entrar/?lang=pt-br&amp;next=%2Fes%2Ftree%2F"')
        self.assertContains(response, 'href="/entrar/?lang=es&amp;next=%2Fes%2Ftree%2F"')
        self.assertNotContains(response, "<script")
        self.assertNotContains(response, " onclick=")

    def test_flag_on_the_password_page_changes_and_keeps_the_language(self):
        response = self.client.get("/entrar/?lang=es", HTTP_ACCEPT_LANGUAGE="pt-br")
        self.assertContains(response, "Contraseña")
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, "es")

        self.assertContains(self.client.get("/entrar/", HTTP_ACCEPT_LANGUAGE="pt-br"), "Contraseña")

    def test_chosen_language_is_remembered(self):
        self.enter()

        response = self.client.get("/es/")
        cookie = response.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual(cookie.value, "es")
        self.assertGreaterEqual(cookie["max-age"], 364 * 24 * 3600)
        self.assertEqual(cookie["samesite"], "Lax")

        response = self.client.get("/", HTTP_ACCEPT_LANGUAGE="pt-br")
        self.assertRedirects(response, "/es/", fetch_redirect_response=False)


class GateSwitchTests(TestCase):
    @override_settings(RAIZES_VIEW_GATE=False)
    def test_gate_switched_off_lets_everything_through(self):
        SiteSettings.get().set_view_password(PASSWORD)

        self.assertEqual(self.client.get("/pt-br/").status_code, 200)


@override_settings(RAIZES_VIEW_GATE=True)
class ExportThroughTheGateTests(DemoFamilyTestCase):
    def test_export_is_not_blocked_by_the_password(self):
        SiteSettings.get().set_view_password(PASSWORD)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        output = Path(folder.name) / "dist"

        export_site(output)

        self.assertIn("<h1>Novidades</h1>", (output / "pt-br" / "index.html").read_text(encoding="utf-8"))

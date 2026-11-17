"""Panel pages: site settings and connected devices."""
import datetime
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from access.middleware import SESSION_KEY
from access.models import SiteSettings, ViewerDevice
from access.roles import REVIEWERS
from access.tests.test_admin_login import PASSWORD, make_staff
from family.export import export_site
from family.tests.base import DemoFamilyTestCase

OLD = "senha-antiga-1"
NEW = "senha-nova-123"


def make_device(site, name="Tablet", minutes_ago=0, **extra):
    return ViewerDevice.objects.create(
        name=name,
        password_version=site.password_version,
        last_seen=timezone.now() - datetime.timedelta(minutes=minutes_ago),
        **extra,
    )


class SettingsPageTests(TestCase):
    def setUp(self):
        self.owner = make_staff(superuser=True)
        self.client.force_login(self.owner)
        self.site = SiteSettings.get()
        self.site.set_view_password(OLD)
        self.url = reverse("admin:access_sitesettings_change", args=[1])

    def post(self, new=NEW, repeat=NEW, family_name="Família Teste"):
        return self.client.post(
            self.url,
            {
                "family_name": family_name,
                "central_person": "",
                "new_view_password": new,
                "repeat_view_password": repeat,
            },
            follow=True,
        )

    def test_changing_the_view_password_in_the_panel(self):
        device = make_device(SiteSettings.get())
        response = self.post()
        site = SiteSettings.get()
        self.assertFalse(site.check_view_password(OLD))
        self.assertTrue(site.check_view_password(NEW))
        self.assertFalse(ViewerDevice.objects.get(pk=device.pk).is_valid(site))
        self.assertContains(response, "desconectados")
        self.assertEqual(site.family_name, "Família Teste")

    def test_blank_password_keeps_the_old_one(self):
        self.post(new="", repeat="")
        site = SiteSettings.get()
        self.assertTrue(site.check_view_password(OLD))
        self.assertEqual(site.password_version, 2)

    def test_passwords_must_match_and_be_long_enough(self):
        self.post(new=NEW, repeat="outra-coisa-99")
        self.assertTrue(SiteSettings.get().check_view_password(OLD))
        self.post(new="1234567", repeat="1234567")
        self.assertTrue(SiteSettings.get().check_view_password(OLD))
        self.post(new="12345678", repeat="12345678")
        self.assertTrue(SiteSettings.get().check_view_password("12345678"))

    def test_settings_page_cannot_add_or_delete(self):
        self.assertEqual(self.client.get(reverse("admin:access_sitesettings_add")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:access_sitesettings_delete", args=[1])).status_code, 403)
        response = self.client.get(reverse("admin:access_sitesettings_changelist"), follow=True)
        self.assertEqual(response.redirect_chain[-1][0], self.url)

    def test_settings_page_says_language_is_in_the_installer(self):
        self.assertContains(self.client.get(self.url), ".env")

    def test_settings_page_says_the_cloudflare_site_has_its_own_password(self):
        for language, words in (("pt-br", "tem a sua própria senha"), ("es", "tiene su propia contraseña")):
            with self.subTest(language=language):
                response = self.client.get(self.url, HTTP_ACCEPT_LANGUAGE=language)
                self.assertContains(response, words)
                self.assertContains(response, "npx wrangler pages secret put SITE_PASSWORD")


class ConnectedPageTests(TestCase):
    def setUp(self):
        self.client.force_login(make_staff(superuser=True))
        self.site = SiteSettings.get()
        self.site.set_view_password(OLD)
        self.url = reverse("admin:access_viewerdevice_changelist")

    def test_connected_page_shows_online_devices_first(self):
        make_device(self.site, "Antigo", minutes_ago=60)
        make_device(self.site, "Agora", minutes_ago=0)
        content = self.client.get(self.url).content.decode()
        self.assertLess(content.index("Agora"), content.index("Antigo"))
        online = self.client.get(self.url + "?online=yes").content.decode()
        self.assertIn("Agora", online)
        self.assertNotIn("Antigo", online)

    def test_disconnect_action(self):
        device = make_device(self.site)
        response = self.client.post(
            self.url, {"action": "disconnect", "_selected_action": [str(device.pk)]}, follow=True
        )
        self.assertTrue(ViewerDevice.objects.get(pk=device.pk).revoked)
        self.assertEqual(response.status_code, 200)

    def test_connected_page_refreshes_itself(self):
        self.assertContains(self.client.get(self.url), '<meta http-equiv="refresh" content="30">')
        other = reverse("admin:access_sitesettings_change", args=[1])
        self.assertNotContains(self.client.get(other), 'http-equiv="refresh"')

    def test_connected_page_is_read_only(self):
        self.assertEqual(self.client.get(reverse("admin:access_viewerdevice_add")).status_code, 403)
        device = make_device(self.site)
        self.client.post(
            reverse("admin:access_viewerdevice_change", args=[device.pk]), {"name": "X"}
        )
        self.assertEqual(ViewerDevice.objects.get(pk=device.pk).name, "Tablet")


class LeaveButtonTests(DemoFamilyTestCase):
    def test_button_for_a_viewer_only(self):
        site = SiteSettings.get()
        device = make_device(site)
        self.assertNotContains(self.client.get("/pt-br/"), 'action="/sair/"')
        session = self.client.session
        session[SESSION_KEY] = str(device.pk)
        session.save()
        response = self.client.get("/pt-br/")
        self.assertContains(response, 'action="/sair/"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_no_button_for_staff(self):
        device = make_device(SiteSettings.get())
        self.client.force_login(make_staff(superuser=True))
        session = self.client.session
        session[SESSION_KEY] = str(device.pk)
        session.save()
        self.assertNotContains(self.client.get("/pt-br/"), 'action="/sair/"')

    def test_no_button_in_the_export(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        output = Path(folder.name) / "dist"
        export_site(output)
        html = (output / "pt-br" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("/sair/", html)


class ReadOnlyAndSecrecyTests(TestCase):
    def setUp(self):
        self.site = SiteSettings.get()
        self.site.set_view_password(OLD)
        self.devices = reverse("admin:access_viewerdevice_changelist")
        self.settings_url = reverse("admin:access_sitesettings_change", args=[1])

    def test_reviewer_cannot_disconnect_or_change_the_password(self):
        reviewer = make_staff(email="rev@example.com", username="rev", group=REVIEWERS)
        self.client.force_login(reviewer)
        device = make_device(self.site)
        self.client.post(self.devices, {"action": "disconnect", "_selected_action": [str(device.pk)]})
        self.assertFalse(ViewerDevice.objects.get(pk=device.pk).revoked)
        before = SiteSettings.get()
        self.client.post(
            self.settings_url,
            {"family_name": "X", "new_view_password": NEW, "repeat_view_password": NEW},
        )
        after = SiteSettings.get()
        self.assertEqual(after.view_password_hash, before.view_password_hash)
        self.assertEqual(after.password_version, before.password_version)
        self.assertTrue(after.check_view_password(OLD))

    def test_no_delete_action_or_url(self):
        self.client.force_login(make_staff(superuser=True))
        device = make_device(self.site)
        response = self.client.get(self.devices)
        self.assertNotContains(response, "delete_selected")
        self.client.post(self.devices, {"action": "delete_selected", "_selected_action": [str(device.pk)], "post": "yes"})
        self.assertTrue(ViewerDevice.objects.filter(pk=device.pk).exists())
        url = reverse("admin:access_viewerdevice_delete", args=[device.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, {"post": "yes"}).status_code, 403)
        self.assertTrue(ViewerDevice.objects.filter(pk=device.pk).exists())

    def test_form_error_does_not_echo_the_typed_password(self):
        self.client.force_login(make_staff(superuser=True))
        response = self.client.post(
            self.settings_url,
            {"family_name": "X", "new_view_password": "segredo-digitado-1", "repeat_view_password": "outro-valor-22"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "segredo-digitado-1")
        self.assertNotContains(response, "outro-valor-22")

    def test_blank_spaces_get_their_own_message(self):
        self.client.force_login(make_staff(superuser=True))
        response = self.client.post(
            self.settings_url,
            {"family_name": "X", "new_view_password": "         ", "repeat_view_password": "         "},
        )
        self.assertContains(response, "só espaços")
        self.assertNotContains(response, "pelo menos 8")

    def test_settings_list_is_forbidden_without_permission(self):
        user = make_staff(email="n@example.com", username="nada")
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("admin:access_sitesettings_changelist")).status_code, 403)

    def test_status_column_does_not_query_per_row(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.client.force_login(make_staff(superuser=True))
        make_device(self.site, "D0")
        self.client.get(self.devices)
        with CaptureQueriesContext(connection) as one:
            self.client.get(self.devices)
        for i in range(1, 5):
            make_device(self.site, f"D{i}")
        with CaptureQueriesContext(connection) as many:
            self.client.get(self.devices)
        self.assertEqual(len(one), len(many))

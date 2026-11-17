import datetime

from django.test import TestCase, override_settings
from django.utils import timezone

from access import config
from access.devices import describe_browser, ip_prefix
from access.models import SiteSettings, ViewerDevice
from family.models import Person

ANDROID_CHROME = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
)
IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)


class SiteSettingsTests(TestCase):
    def test_view_password_is_stored_only_as_a_hash(self):
        site = SiteSettings.get()
        self.assertFalse(site.has_view_password)
        site.set_view_password("bolo-de-fuba")
        self.assertNotIn("bolo-de-fuba", site.view_password_hash)
        self.assertTrue(site.has_view_password)
        self.assertTrue(site.check_view_password("bolo-de-fuba"))
        self.assertFalse(site.check_view_password("errada"))

    def test_changing_the_password_bumps_the_version(self):
        site = SiteSettings.get()
        self.assertEqual(site.password_version, 1)
        site.set_view_password("um")
        self.assertEqual(site.password_version, 2)
        site.set_view_password("dois")
        self.assertEqual(SiteSettings.get().password_version, 3)

    def test_get_always_returns_the_same_row(self):
        SiteSettings.get()
        SiteSettings.get()
        self.assertEqual(SiteSettings.objects.count(), 1)

    @override_settings(RAIZES_FAMILY_NAME="Env Family", RAIZES_CENTRAL_PERSON="env-person")
    def test_settings_override_the_env_values(self):
        self.assertEqual(config.family_name(), "Env Family")
        self.assertEqual(config.central_person_identifier(), "env-person")
        person = Person.objects.create(identifier="db-person", given_name="Ana")
        site = SiteSettings.get()
        site.family_name = "Db Family"
        site.central_person = person
        site.save()
        self.assertEqual(config.family_name(), "Db Family")
        self.assertEqual(config.central_person_identifier(), "db-person")


class ViewerDeviceTests(TestCase):
    def make(self, **kwargs):
        return ViewerDevice.objects.create(password_version=1, **kwargs)

    def test_device_is_invalid_after_a_password_change_or_when_revoked(self):
        site = SiteSettings.get()
        device = self.make()
        self.assertTrue(device.is_valid(site))
        site.set_view_password("nova")
        self.assertFalse(device.is_valid(site))
        device.password_version = site.password_version
        self.assertTrue(device.is_valid(site))
        device.revoked = True
        self.assertFalse(device.is_valid(site))

    def test_device_is_online_for_five_minutes(self):
        device = self.make()
        device.last_seen = timezone.now() - datetime.timedelta(minutes=4)
        self.assertTrue(device.is_online)
        device.last_seen = timezone.now() - datetime.timedelta(minutes=6)
        self.assertFalse(device.is_online)


class DevicesHelpersTests(TestCase):
    def test_ip_prefix_hides_the_end(self):
        self.assertEqual(ip_prefix("192.168.1.37"), "192.168.1.x")
        self.assertEqual(ip_prefix("2804:14c:5b80:8d2::1"), "2804:14c:…")
        self.assertEqual(ip_prefix(""), "")

    def test_describe_browser(self):
        self.assertEqual(describe_browser(ANDROID_CHROME), "Chrome · Android")
        self.assertEqual(describe_browser(IPHONE_SAFARI), "Safari · iPhone")
        self.assertEqual(describe_browser("curl/8"), "?")
        self.assertEqual(describe_browser(""), "?")

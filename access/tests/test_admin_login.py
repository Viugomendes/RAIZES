"""The admin panel at /painel/: e-mail login, password reset, roles and headers."""
import re
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings

from access.models import SiteSettings
from access.roles import ADMINISTRATORS, REVIEWERS
from access.security import CONTENT_SECURITY_POLICY

EMAIL = "dona@example.com"
PASSWORD = "uma-senha-comprida-42"
STAFF_SESSION_AGE = 12 * 60 * 60


def make_staff(email=EMAIL, username="dona", group=None, superuser=False):
    users = get_user_model().objects
    if superuser:
        user = users.create_superuser(username, email=email, password=PASSWORD)
    else:
        user = users.create_user(username, email=email, password=PASSWORD, is_staff=True)
    if group:
        user.groups.add(Group.objects.get(name=group))
    return user


class AdminLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.owner = make_staff(superuser=True)

    def log_in(self, email=EMAIL, password=PASSWORD):
        return self.client.post(
            "/painel/login/", {"username": email, "password": password, "next": "/painel/"}
        )

    def test_admin_logs_in_with_e_mail_and_password(self):
        response = self.log_in(email="Dona@Example.com")

        self.assertRedirects(response, "/painel/")
        self.assertEqual(self.client.get("/painel/").status_code, 200)

    def test_login_page_asks_for_the_e_mail_and_links_to_the_reset(self):
        response = self.client.get("/painel/login/")

        self.assertContains(response, 'type="email"')
        self.assertContains(response, "E-mail")
        self.assertContains(response, 'href="/painel/senha/"')
        self.assertContains(response, "Esqueci a senha")

    def test_login_by_username_or_wrong_password_fails(self):
        for email, password in (("dona", PASSWORD), (EMAIL, "errada")):
            with self.subTest(email=email):
                response = self.log_in(email, password)

                self.assertEqual(response.status_code, 200)
                self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_or_non_staff_user_cannot_log_in(self):
        users = get_user_model().objects
        users.create_user("primo", email="primo@example.com", password=PASSWORD)
        users.create_user(
            "tia", email="tia@example.com", password=PASSWORD, is_staff=True, is_active=False
        )
        for email in ("primo@example.com", "tia@example.com"):
            with self.subTest(email=email):
                self.log_in(email)

                self.assertNotIn("_auth_user_id", self.client.session)

    def test_ten_wrong_admin_logins_block_for_a_while(self):
        for _attempt in range(10):
            self.assertEqual(self.log_in(password="errada").status_code, 200)

        blocked = self.log_in()

        self.assertEqual(blocked.status_code, 429)
        self.assertContains(blocked, "Muitas tentativas erradas", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_a_good_login_clears_the_wrong_attempts(self):
        for _attempt in range(9):
            self.log_in(password="errada")
        self.assertRedirects(self.log_in(), "/painel/")
        self.client.logout()

        for _attempt in range(9):
            self.log_in(password="errada")

        self.assertRedirects(self.log_in(), "/painel/")

    def test_password_reset_sends_an_e_mail(self):
        response = self.client.post("/painel/senha/", {"email": EMAIL})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [EMAIL])
        self.assertEqual(mail.outbox[0].from_email, settings.DEFAULT_FROM_EMAIL)
        link = re.search(r"https?://[^/\s]+(/painel/senha/\S+)", mail.outbox[0].body)
        self.assertIsNotNone(link, mail.outbox[0].body)

        # The link opens the form for a new password, which then works.
        form_page = self.client.get(link[1], follow=True)
        self.assertEqual(form_page.status_code, 200)
        done = self.client.post(
            form_page.redirect_chain[-1][0],
            {"new_password1": "outra-senha-comprida-7", "new_password2": "outra-senha-comprida-7"},
        )
        self.assertRedirects(done, "/painel/senha/pronto/")
        self.assertRedirects(self.log_in(password="outra-senha-comprida-7"), "/painel/")

    def test_old_admin_address_is_gone(self):
        response = self.client.get("/admin/", follow=True)

        self.assertEqual(response.status_code, 404)

    @override_settings(RAIZES_VIEW_GATE=True)
    def test_admin_login_after_the_view_password_lasts_12_hours(self):
        site = SiteSettings.get()
        site.set_view_password("bolo-de-fuba")
        self.client.post("/entrar/", {"password": "bolo-de-fuba", "next": "/pt-br/"})
        self.assertGreater(self.client.session.get_expiry_age(), STAFF_SESSION_AGE)

        self.assertRedirects(self.log_in(), "/painel/")

        self.assertEqual(self.client.session.get_expiry_age(), STAFF_SESSION_AGE)


class SecurityHeadersTests(TestCase):
    def test_every_response_has_the_security_headers(self):
        for path in ("/pt-br/", "/painel/login/", "/painel/", "/nao-existe/", "/robots.txt"):
            with self.subTest(path=path):
                response = self.client.get(path)

                self.assertEqual(response["Content-Security-Policy"], CONTENT_SECURITY_POLICY)
                self.assertEqual(response["X-Frame-Options"], "DENY")
                self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")
                self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")

    def test_policy_is_the_same_as_the_cloudflare_function(self):
        source = (Path(settings.BASE_DIR) / "functions" / "_middleware.js").read_text("utf-8")
        block = re.search(r"CONTENT_SECURITY_POLICY = \[(.*?)\]\.join", source, re.DOTALL)[1]
        parts = re.findall(r'"([^"]*)"', block)

        self.assertEqual(CONTENT_SECURITY_POLICY, "; ".join(parts))


class RoleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_roles_exist_after_migrate(self):
        ours = Permission.objects.filter(content_type__app_label__in=("family", "access"))
        administrators = Group.objects.get(name=ADMINISTRATORS).permissions.all()
        reviewers = Group.objects.get(name=REVIEWERS).permissions.all()

        self.assertTrue(ours.exists())
        self.assertQuerySetEqual(administrators, ours, ordered=False)
        self.assertQuerySetEqual(
            reviewers, ours.filter(codename__startswith="view_"), ordered=False
        )

    def test_reviewer_sees_but_cannot_change(self):
        self.client.force_login(make_staff(group=REVIEWERS))

        self.assertEqual(self.client.get("/painel/family/person/").status_code, 200)
        self.assertEqual(self.client.get("/painel/family/person/add/").status_code, 403)
        self.assertEqual(self.client.post("/painel/family/person/add/", {}).status_code, 403)

    def test_administrator_cannot_manage_accounts(self):
        self.client.force_login(make_staff(group=ADMINISTRATORS))

        self.assertEqual(self.client.get("/painel/family/person/add/").status_code, 200)
        self.assertEqual(self.client.get("/painel/auth/user/").status_code, 403)
        self.assertEqual(self.client.get("/painel/auth/group/").status_code, 403)

    def test_owner_manages_accounts(self):
        self.client.force_login(make_staff(superuser=True))

        self.assertEqual(self.client.get("/painel/auth/user/").status_code, 200)
        self.assertEqual(self.client.get("/painel/auth/group/").status_code, 200)

"""Commands to install, serve, back up and restore (never touching data/ or demo/)."""
import io
import logging
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from unittest import mock

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase, override_settings

from access.models import SiteSettings
from access.passwords import generate_admin_password

EMAIL = "dona@example.com"


def run(name, *args, **options):
    out = io.StringIO()
    call_command(name, *args, stdout=out, stderr=io.StringIO(), **options)
    return out.getvalue()


def password_in(text, user):
    """The word of the text that is the user's password."""
    for word in text.split():
        word = word.strip(".,:;")
        if user.check_password(word):
            return word
    return None


class TempProject:
    """A temporary data folder, .env and backups folder, in place of the real ones."""

    def setUp(self):
        super().setUp()
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.data = self.root / "data"
        self.data.mkdir()
        self.env = self.root / ".env"
        self.backups = self.root / "backups"
        override = override_settings(
            DATA_DIR=self.data,
            DATABASE_FILE=self.data / "raizes.sqlite3",
            ENV_FILE=self.env, RAIZES_BACKUP_DIR=self.backups
        )
        override.enable()
        self.addCleanup(override.disable)


class PasswordTests(SimpleTestCase):
    def test_generated_password_is_strong(self):
        first, second = generate_admin_password(), generate_admin_password()

        self.assertEqual(len(first), 16)
        self.assertTrue(first.isalnum())
        self.assertFalse(set(first + second) & set("0O1lI"))
        self.assertNotEqual(first, second)


@override_settings(RAIZES_EMAIL_CONFIGURED=True)
class InstallTests(TempProject, TestCase):
    def install(self, **extra):
        options = dict(
            family_name="Família Teste",
            language="es",
            email=EMAIL,
            view_password="senha-da-familia",
            no_input=True,
        )
        options.update(extra)
        return run("instalar", **options)

    def test_install_creates_the_admin_and_e_mails_the_password(self):
        self.install()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, [EMAIL])
        user = get_user_model().objects.get(email=EMAIL)
        self.assertTrue(user.is_superuser and user.is_staff)
        self.assertEqual(user.username, EMAIL)
        password = password_in(message.body, user)
        self.assertTrue(password)
        self.assertTrue(self.client.login(username=EMAIL, password=password))
        self.assertEqual(self.client.get("/painel/").status_code, 200)

    def test_install_sets_the_view_password_and_the_family_name(self):
        self.install()

        site = SiteSettings.get()
        self.assertTrue(site.check_view_password("senha-da-familia"))
        self.assertEqual(site.family_name, "Família Teste")
        env = self.env.read_text(encoding="utf-8")
        self.assertIn("RAIZES_LANGUAGE=es", env)
        self.assertIn("Família Teste", env)
        self.assertNotIn("senha-da-familia", env)

    def test_install_turns_debug_off_in_env(self):
        self.install()

        self.assertIn("RAIZES_DEBUG=false", self.env.read_text(encoding="utf-8"))

    def test_failed_env_write_creates_nothing(self):
        with mock.patch(
            "access.management.commands.instalar.set_env_values", side_effect=OSError("read-only")
        ):
            with self.assertRaises(CommandError):
                self.install()

        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(SiteSettings.get().has_view_password)
        self.assertEqual(mail.outbox, [])

    def test_install_keeps_the_other_lines_of_env(self):
        self.env.write_text("# mine\nRAIZES_SECRET_KEY='x#y'\nRAIZES_LANGUAGE=pt-br\n", "utf-8")

        self.install()

        env = self.env.read_text(encoding="utf-8")
        self.assertIn("# mine\nRAIZES_SECRET_KEY='x#y'\n", env)
        self.assertEqual(env.count("RAIZES_LANGUAGE"), 1)

    def test_install_refuses_a_second_admin_with_the_same_e_mail(self):
        self.install()

        with self.assertRaises(CommandError):
            self.install(email="DONA@example.com")
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_install_refuses_a_short_view_password_and_a_wrong_language(self):
        for extra in ({"view_password": "curta"}, {"view_password": "   "}, {"language": "fr"}):
            with self.subTest(extra=extra), self.assertRaises(CommandError):
                self.install(**extra)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(self.env.exists())

    def test_install_without_input_needs_every_option(self):
        with self.assertRaises(CommandError):
            run("instalar", no_input=True, email=EMAIL)

    def test_failed_e_mail_prints_the_password_once_and_explains(self):
        with mock.patch(
            "access.management.commands.instalar.send_mail", side_effect=OSError("down")
        ), self.assertLogs(level="DEBUG") as logs:
            logging.getLogger("probe").debug("probe")
            output = self.install()

        user = get_user_model().objects.get(email=EMAIL)
        password = password_in(output, user)
        self.assertTrue(password)
        self.assertEqual(output.count(password), 1)
        self.assertIn("README", output)
        self.assertNotIn(password, "\n".join(logs.output))

    @override_settings(RAIZES_EMAIL_CONFIGURED=False)
    def test_without_e_mail_settings_the_password_is_shown_and_never_written_to_a_file(self):
        output = self.install()

        user = get_user_model().objects.get(email=EMAIL)
        password = password_in(output, user)
        self.assertTrue(password)
        self.assertEqual(output.count(password), 1)
        # Not even to the folder of e-mail files.
        self.assertEqual(mail.outbox, [])

    def test_interactive_install_asks_twice_with_getpass(self):
        answers = iter(["Família Teste", "pt-br", EMAIL])
        with mock.patch("builtins.input", lambda prompt="": next(answers)), mock.patch(
            "getpass.getpass", side_effect=["senha-da-familia", "senha-da-familia"]
        ) as asked:
            run("instalar")

        self.assertEqual(asked.call_count, 2)
        self.assertTrue(SiteSettings.get().check_view_password("senha-da-familia"))

    def test_interactive_install_refuses_passwords_that_differ(self):
        answers = iter(["Família Teste", "pt-br", EMAIL])
        with mock.patch("builtins.input", lambda prompt="": next(answers)), mock.patch(
            "getpass.getpass", side_effect=["senha-da-familia", "outra-senha-aqui"]
        ):
            with self.assertRaises(CommandError):
                run("instalar")
        self.assertFalse(get_user_model().objects.exists())


class BackupTests(TempProject, TestCase):
    def fill(self):
        database = sqlite3.connect(self.data / "raizes.sqlite3")
        database.execute("create table person (name text)")
        database.executemany("insert into person values (?)", [("Ana",), ("Rui",)])
        database.commit()
        database.close()
        (self.data / "media").mkdir()
        (self.data / "media" / "foto.jpg").write_bytes(b"jpeg-bytes")
        (self.data / "cache").mkdir()
        (self.data / "cache" / "small.jpg").write_bytes(b"copy")
        self.env.write_text("RAIZES_LANGUAGE=es\n", "utf-8")

    def rows(self):
        database = sqlite3.connect(self.data / "raizes.sqlite3")
        try:
            return database.execute("select name from person order by name").fetchall()
        finally:
            database.close()

    def make_backup(self):
        run("backup")
        (archive,) = self.backups.glob("raizes-*.zip")
        return archive

    def empty_data(self):
        for path in sorted(self.data.rglob("*"), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()

    def test_backup_and_restore_keep_everything(self):
        self.fill()
        archive = self.make_backup()
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
        self.assertIn(".env", names)
        self.assertFalse([name for name in names if "cache" in name])
        self.assertRegex(archive.name, r"^raizes-\d{4}-\d{2}-\d{2}-\d{6}\.zip$")

        self.empty_data()
        self.env.unlink()
        run("restaurar", str(archive))

        self.assertEqual(self.rows(), [("Ana",), ("Rui",)])
        self.assertEqual((self.data / "media" / "foto.jpg").read_bytes(), b"jpeg-bytes")
        self.assertEqual(self.env.read_text("utf-8"), "RAIZES_LANGUAGE=es\n")
        self.assertFalse((self.data / "cache").exists())

    def test_restore_refuses_to_overwrite_without_force(self):
        self.fill()
        archive = self.make_backup()
        (self.data / "media" / "foto.jpg").write_bytes(b"newer")

        with self.assertRaises(CommandError):
            run("restaurar", str(archive))
        self.assertEqual((self.data / "media" / "foto.jpg").read_bytes(), b"newer")

        run("restaurar", str(archive), force=True)
        self.assertEqual((self.data / "media" / "foto.jpg").read_bytes(), b"jpeg-bytes")

    def test_restore_refuses_a_different_env_without_force(self):
        self.fill()
        archive = self.make_backup()
        self.empty_data()
        self.env.write_text("RAIZES_LANGUAGE=pt-br\n", "utf-8")

        with self.assertRaises(CommandError):
            run("restaurar", str(archive))
        self.assertEqual(self.env.read_text("utf-8"), "RAIZES_LANGUAGE=pt-br\n")

    def test_restore_rejects_zip_slip_entries(self):
        bad_names = (
            "../evil.txt",
            "data/../../evil.txt",
            "/abs/evil.txt",
            "C:/evil.txt",
            "..\\evil.txt",
        )
        for bad in bad_names:
            with self.subTest(entry=bad):
                archive = self.root / "bad.zip"
                with zipfile.ZipFile(archive, "w") as zipped:
                    zipped.writestr("data/ok.txt", "fine")
                    zipped.writestr(bad, "evil")
                with self.assertRaises(CommandError):
                    run("restaurar", str(archive))
                self.assertFalse((self.root.parent / "evil.txt").exists())
                self.assertFalse((self.root / "evil.txt").exists())
                self.assertFalse((self.data / "ok.txt").exists())

    def test_backup_is_a_consistent_snapshot_without_journal_files(self):
        self.fill()
        (self.data / "raizes.sqlite3-wal").write_bytes(b"wal")
        (self.data / "raizes.sqlite3-shm").write_bytes(b"shm")
        (self.data / "raizes.sqlite3-journal").write_bytes(b"journal")
        archive = self.make_backup()

        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            self.assertIn("data/raizes.sqlite3", names)
            self.assertFalse([n for n in names if n.endswith(("-wal", "-shm", "-journal"))])
            copy = self.root / "copy.sqlite3"
            copy.write_bytes(zipped.read("data/raizes.sqlite3"))
        database = sqlite3.connect(copy)
        try:
            rows = database.execute("select name from person order by name").fetchall()
        finally:
            database.close()
        self.assertEqual(rows, [("Ana",), ("Rui",)])

    def test_backup_copies_other_db_files_as_they_are(self):
        self.fill()
        thumbs = self.data / "media" / "photos"
        thumbs.mkdir()
        (thumbs / "Thumbs.db").write_bytes(b"not sqlite at all")
        archive = self.make_backup()

        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.read("data/media/photos/Thumbs.db"), b"not sqlite at all")

    def test_failed_backup_leaves_no_half_written_zip(self):
        self.fill()
        with mock.patch(
            "access.management.commands.backup.snapshot", side_effect=sqlite3.Error("boom")
        ):
            with self.assertRaises(CommandError):
                run("backup")

        self.assertEqual(list(self.backups.glob("*")), [])

    def test_backup_never_overwrites_an_existing_file(self):
        self.fill()
        self.make_backup()

        with self.assertRaises(CommandError):
            run("backup")
        self.assertEqual(len(list(self.backups.glob("raizes-*.zip"))), 1)

    def test_restore_rejects_a_colon_in_any_component(self):
        for bad in ("data/a.txt:stream", "data/sub:x/a.txt", "data/a/b:c"):
            with self.subTest(entry=bad):
                archive = self.root / "bad.zip"
                with zipfile.ZipFile(archive, "w") as zipped:
                    zipped.writestr(bad, "x")
                with self.assertRaises(CommandError):
                    run("restaurar", str(archive))

    def test_restore_rejects_a_missing_or_foreign_archive(self):
        with self.assertRaises(CommandError):
            run("restaurar", str(self.root / "nope.zip"))
        archive = self.root / "other.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            zipped.writestr("something/else.txt", "x")
        with self.assertRaises(CommandError):
            run("restaurar", str(archive))


@override_settings(ALLOWED_HOSTS=["localhost"], CSRF_TRUSTED_ORIGINS=[], RAIZES_PROXY_HEADER="")
class ServeTests(SimpleTestCase):
    def serve(self, ip="192.168.0.7", **options):
        with mock.patch("waitress.serve") as serve, mock.patch(
            "access.management.commands.servir.network_ip", return_value=ip
        ), mock.patch("access.management.commands.servir.call_command") as collect:
            output = run("servir", **options)
        self.collect = collect
        return serve, output

    def test_static_files_are_collected_quietly_before_serving(self):
        self.serve()

        self.collect.assert_called_once_with("collectstatic", interactive=False, verbosity=0)

    @override_settings(DEBUG=False)
    def test_network_flag_allows_the_network_address_for_this_run(self):
        from django.conf import settings

        self.serve(rede=True, port=8123)

        self.assertIn("192.168.0.7", settings.ALLOWED_HOSTS)
        self.assertIn("localhost", settings.ALLOWED_HOSTS)
        self.assertNotIn("*", settings.ALLOWED_HOSTS)
        self.assertIn("http://192.168.0.7:8123", settings.CSRF_TRUSTED_ORIGINS)

    def test_local_serve_allows_no_network_address(self):
        from django.conf import settings

        self.serve()

        self.assertEqual(settings.ALLOWED_HOSTS, ["localhost"])

    @override_settings(DEBUG=False, RAIZES_PROXY_HEADER="CF-Connecting-IP")
    def test_network_flag_is_refused_behind_a_proxy(self):
        # Anybody on the network could then type the proxy's header.
        with mock.patch("waitress.serve") as serve, mock.patch(
            "access.management.commands.servir.call_command"
        ):
            with self.assertRaises(CommandError):
                run("servir", rede=True)
        serve.assert_not_called()

    def test_default_host_is_local_only(self):
        serve, output = self.serve()

        kwargs = serve.call_args.kwargs
        self.assertEqual((kwargs["host"], kwargs["port"], kwargs["threads"]), ("127.0.0.1", 8000, 8))
        self.assertIn("http://localhost:8000/", output)
        self.assertNotIn("192.168.0.7", output)

    @override_settings(DEBUG=True)
    def test_network_with_debug_on_refuses_to_start(self):
        for options in ({"rede": True}, {"host": "0.0.0.0"}):
            with self.subTest(options=options), mock.patch("waitress.serve") as serve:
                with self.assertRaises(CommandError):
                    run("servir", **options)
                serve.assert_not_called()

    @override_settings(DEBUG=False)
    def test_network_flag_binds_everywhere_and_prints_both_addresses(self):
        serve, output = self.serve(rede=True, port=8123)

        self.assertEqual(serve.call_args.kwargs["host"], "0.0.0.0")
        self.assertIn("http://localhost:8123/", output)
        self.assertIn("http://192.168.0.7:8123/", output)

    @override_settings(DEBUG=True)
    def test_local_host_is_allowed_with_debug_on(self):
        serve, _output = self.serve(port=8001)

        self.assertEqual(serve.call_args.kwargs["port"], 8001)

    @override_settings(DEBUG=False)
    def test_serve_without_a_network_prints_only_the_local_address(self):
        _serve, output = self.serve(ip=None, rede=True)

        self.assertIn("http://localhost:8000/", output)

    def test_network_ip_sends_nothing_and_survives_no_network(self):
        from access.management.commands.servir import network_ip

        with mock.patch("socket.socket") as fake:
            sock = fake.return_value.__enter__.return_value
            sock.getsockname.return_value = ("10.0.0.5", 1)
            self.assertEqual(network_ip(), "10.0.0.5")
            sock.send.assert_not_called()
            sock.getsockname.side_effect = OSError
            self.assertIsNone(network_ip())


class DemoPasswordTests(TestCase):
    def test_load_demo_sets_and_prints_the_demo_view_password(self):
        counts = dict(people=1, unions=0, places=0, photos=0, clips=0, recipes=0)
        with override_settings(RAIZES_DATASET="demo"), mock.patch(
            "family.management.commands.load_demo.load_demo_family", return_value=counts
        ):
            output = run("load_demo")

        self.assertTrue(SiteSettings.get().check_view_password("demo-raizes"))
        self.assertIn("demo-raizes", output)

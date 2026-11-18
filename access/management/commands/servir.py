"""`python manage.py servir`: serves the site on the home network with waitress.

One process only: the attempt limits (access/ratelimit.py) are counted in memory.
"""
import socket

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext as _


def network_ip():
    """The address of this computer on the local network, or None.

    A UDP "connect" only chooses the route: no packet is ever sent.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))
            return sock.getsockname()[0]
    except OSError:
        return None


def waitress_options():
    """Behind a tunnel or a proxy, waitress keeps its forwarded headers.

    By default waitress deletes them. Only the proxy on this computer is trusted,
    and only for the headers it sets: the scheme (https) and, with Caddy, the
    visitor's address (waitress keeps only the last X-Forwarded-For entry).
    """
    if not settings.RAIZES_PROXY_HEADER:
        return {}
    headers = {"x-forwarded-proto"}
    if settings.RAIZES_PROXY_HEADER == "X-Forwarded-For":
        headers.add("x-forwarded-for")
    return {"trusted_proxy": "127.0.0.1", "trusted_proxy_headers": headers}


class Command(BaseCommand):
    # Translated when argparse reads it (a lazy text crashes `--help`).
    @property
    def help(self):
        return _("Serves the site and the panel to the devices of the home network.")

    def add_arguments(self, parser):
        parser.add_argument("--port", type=int, default=8000, help=_("Port (default 8000)."))
        parser.add_argument(
            "--host",
            default="127.0.0.1",
            help=_("Address to listen on (default 127.0.0.1: this computer only)."),
        )
        parser.add_argument(
            "--rede",
            action="store_true",
            help=_("Open the site to the devices of the home network (listens on 0.0.0.0)."),
        )

    def handle(self, *args, **options):
        import waitress

        host, port = options["host"], options["port"]
        if options["rede"]:
            host = "0.0.0.0"
        local_only = host in ("127.0.0.1", "localhost", "::1")
        # Even on this computer only: a tunnel or a proxy may be publishing it.
        if settings.DEBUG:
            raise CommandError(
                _(
                    "Debug mode is on (RAIZES_DEBUG) and it shows pieces of the code, so "
                    "servir does not start. Set RAIZES_DEBUG=false in .env and try again. "
                    "To work on the code, use python manage.py runserver."
                )
            )
        if not settings.RAIZES_VIEW_GATE:
            raise CommandError(
                _(
                    "The view password is off (RAIZES_VIEW_GATE=false), so servir does not "
                    "start: the family site would be open to anybody. Set "
                    "RAIZES_VIEW_GATE=true in .env and try again."
                )
            )
        if not local_only and settings.RAIZES_PROXY_HEADER:
            # Anybody on the network could type the proxy's header and pass for someone else.
            raise CommandError(
                _(
                    "RAIZES_PROXY_HEADER is set, so the site only listens on this computer "
                    "(the tunnel or the proxy brings the visits). Remove --rede or --host."
                )
            )

        # WhiteNoise serves the CSS and JavaScript from STATIC_ROOT: fill it first.
        call_command("collectstatic", interactive=False, verbosity=0)
        # Imported after collectstatic: WhiteNoise lists the files when it starts.
        from config.wsgi import application

        self.stdout.write(_("Open on this computer: http://localhost:%(port)d/") % {"port": port})
        if not local_only:
            addresses = [network_ip()] if host in ("0.0.0.0", "::") else [host]
            for ip in filter(None, addresses):
                self.allow(ip, port)
                self.stdout.write(
                    _("Open on the home network: http://%(ip)s:%(port)d/")
                    % {"ip": ip, "port": port}
                )
        self.stdout.write(_("Press Ctrl+C to stop."))
        waitress.serve(application, host=host, port=port, threads=8, **waitress_options())

    def allow(self, ip, port):
        """Let this run answer at the network address (settings are already loaded)."""
        name = f"[{ip}]" if ":" in ip else ip
        if name not in settings.ALLOWED_HOSTS:
            settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, name]
        settings.CSRF_TRUSTED_ORIGINS = [*settings.CSRF_TRUSTED_ORIGINS, f"http://{name}:{port}"]

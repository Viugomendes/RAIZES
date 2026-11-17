"""`python manage.py servir`: serves the site on the home network with waitress."""
import socket

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import gettext_lazy as _


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


class Command(BaseCommand):
    help = _("Serves the site and the panel to the devices of the home network.")

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

        from config.wsgi import application

        host, port = options["host"], options["port"]
        if options["rede"]:
            host = "0.0.0.0"
        local_only = host in ("127.0.0.1", "localhost", "::1")
        if not local_only and settings.DEBUG:
            raise CommandError(
                _(
                    "Debug mode is on (RAIZES_DEBUG), so the site cannot be opened to the "
                    "network. Set RAIZES_DEBUG=false in .env and try again."
                )
            )
        self.stdout.write(_("Open on this computer: http://localhost:%(port)d/") % {"port": port})
        if not local_only:
            ip = network_ip()
            if ip:
                self.stdout.write(
                    _("Open on the home network: http://%(ip)s:%(port)d/")
                    % {"ip": ip, "port": port}
                )
        self.stdout.write(_("Press Ctrl+C to stop."))
        waitress.serve(application, host=host, port=port, threads=8)

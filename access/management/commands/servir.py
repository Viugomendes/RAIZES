"""`python manage.py servir`: serves the site on the home network with waitress."""
import socket

from django.core.management.base import BaseCommand
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
            default="0.0.0.0",
            help=_("Address to listen on (0.0.0.0 = the whole home network)."),
        )

    def handle(self, *args, **options):
        import waitress

        from config.wsgi import application

        host, port = options["host"], options["port"]
        self.stdout.write(_("Open on this computer: http://localhost:%(port)d/") % {"port": port})
        if host not in ("127.0.0.1", "localhost", "::1"):
            ip = network_ip()
            if ip:
                self.stdout.write(
                    _("Open on the home network: http://%(ip)s:%(port)d/")
                    % {"ip": ip, "port": port}
                )
        self.stdout.write(_("Press Ctrl+C to stop."))
        waitress.serve(application, host=host, port=port, threads=8)

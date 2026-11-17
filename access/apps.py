from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


def sync_roles(using="default", **kwargs):
    """After every migrate: the roles get the permissions of models new to them."""
    from django.contrib.auth.models import Group, Permission

    from . import roles

    roles.sync_roles(Group, Permission, using=using)


class AccessConfig(AppConfig):
    name = "access"
    verbose_name = _("Access")

    def ready(self):
        # Sent for this app after the permissions of family and access exist
        # (auth's own handler runs first, and both apps come before it in order).
        post_migrate.connect(sync_roles, sender=self)

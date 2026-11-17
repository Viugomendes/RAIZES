"""The groups Administradores and Revisores (see access/roles.py)."""
from django.contrib.auth.management import create_permissions
from django.db import migrations

from access.roles import APPS, create_roles


def add_roles(apps, schema_editor):
    # Permissions are normally created after all migrations: create ours now.
    for label in APPS:
        app_config = apps.get_app_config(label)
        app_config.models_module = True
        create_permissions(
            app_config, apps=apps, verbosity=0, using=schema_editor.connection.alias
        )
        app_config.models_module = None
    create_roles(
        apps.get_model("auth", "Group"),
        apps.get_model("auth", "Permission"),
        using=schema_editor.connection.alias,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(add_roles, migrations.RunPython.noop)]

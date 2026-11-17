"""The roles of the panel, kept as Django groups.

The owner is a superuser and can do everything. An administrator edits all the
family data and the site settings, but never accounts or roles (app `auth`). A
reviewer only looks.
"""
ADMINISTRATORS = "Administradores"
REVIEWERS = "Revisores"
APPS = ("family", "access")


def create_roles(group_model, permission_model) -> None:
    """Create both groups and give them their permissions (models passed in for migrations)."""
    ours = permission_model.objects.filter(content_type__app_label__in=APPS)
    administrators, _created = group_model.objects.get_or_create(name=ADMINISTRATORS)
    administrators.permissions.add(*ours)
    reviewers, _created = group_model.objects.get_or_create(name=REVIEWERS)
    reviewers.permissions.add(*ours.filter(codename__startswith="view_"))

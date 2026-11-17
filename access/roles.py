"""The roles of the panel, kept as Django groups.

The owner is a superuser and can do everything. An administrator edits all the
family data and the site settings, but never accounts or roles (app `auth`). A
reviewer only looks.
"""
ADMINISTRATORS = "Administradores"
REVIEWERS = "Revisores"
APPS = ("family", "access")


def _role_permissions(permission_model, using):
    ours = permission_model.objects.using(using).filter(content_type__app_label__in=APPS)
    return {ADMINISTRATORS: ours, REVIEWERS: ours.filter(codename__startswith="view_")}


def create_roles(group_model, permission_model, using="default") -> None:
    """Create both groups with their permissions (the 0002 data migration)."""
    for name, permissions in _role_permissions(permission_model, using).items():
        group, _created = group_model.objects.using(using).get_or_create(name=name)
        group.permissions.add(*permissions)


def sync_roles(group_model, permission_model, using="default") -> None:
    """After a migrate: give each role the permissions of models new to it.

    A model counts as new to a role when the role has none of its permissions.
    Permissions the owner removed from a model the role already has stay
    removed, and a role the owner deleted or renamed is not created again.
    """
    for name, permissions in _role_permissions(permission_model, using).items():
        group = group_model.objects.using(using).filter(name=name).first()
        if group is None:
            continue
        known = set(group.permissions.values_list("content_type_id", flat=True))
        new = [permission for permission in permissions if permission.content_type_id not in known]
        group.permissions.add(*new)

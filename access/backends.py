"""The panel is entered with an e-mail and a password, never a username."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Finds an active staff account by its e-mail (upper or lower case alike).

    Permissions are checked as usual (inherited from ModelBackend).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or kwargs.get("email") or "").strip()
        if not email or password is None:
            return None
        users = get_user_model()._default_manager.filter(
            email__iexact=email, is_active=True, is_staff=True
        )
        # Two accounts with the same e-mail: nobody can tell which one is meant.
        found = list(users[:2])
        if len(found) != 1:
            # Hash anyway, so the answer takes as long as for a wrong password.
            get_user_model()().set_password(password)
            return None
        user = found[0]
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

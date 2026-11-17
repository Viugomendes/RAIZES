"""The password generated for the owner of the panel."""
import secrets
import string

# Letters and digits without the look-alikes 0 O 1 l I.
ALPHABET = "".join(c for c in string.ascii_letters + string.digits if c not in "0O1lI")
LENGTH = 16


def generate_admin_password() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))

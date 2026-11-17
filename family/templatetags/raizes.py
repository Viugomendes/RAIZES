"""Template helpers: `{% load raizes %}`."""
from django import template

from family import images

register = template.Library()

SIZES = {"avatar": images.AVATAR, "thumb": images.THUMB, "large": images.LARGE}


@register.filter
def photo_url(file, size: str) -> str:
    """Address of a smaller copy of a photo: {{ person.photo|photo_url:"avatar" }}."""
    name = getattr(file, "name", file) or ""
    return images.variant_url(name, SIZES[size])

"""Pages of the site.

`distill_path=True` marks a page to be exported as a static file. Pages with a
parameter also say, in `distill_func`, which values exist (one page each).
"""
from django.urls import path

from . import views
from .models import Person

app_name = "family"


def every_person():
    """One page per person: the identifiers to export."""
    return [(identifier,) for identifier in Person.objects.values_list("identifier", flat=True)]


urlpatterns = [
    path("", views.tree, name="tree", distill_path=True),
    path("people/", views.person_list, name="person_list", distill_path=True),
    path(
        "people/<slug:identifier>/",
        views.person_detail,
        name="person_detail",
        distill_path=True,
        distill_func=every_person,
    ),
]

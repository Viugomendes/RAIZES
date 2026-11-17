"""Pages of the site.

`distill_path=True` marks a page to be exported as a static file. Pages with a
parameter also say, in `distill_func`, which values exist (one page each).
"""
from django.urls import path

from . import views
from .models import Person, Recipe

app_name = "family"


def every_person():
    """One page per person: the identifiers to export."""
    return [(identifier,) for identifier in Person.objects.values_list("identifier", flat=True)]


def every_recipe():
    return [(slug,) for slug in Recipe.objects.values_list("slug", flat=True)]


urlpatterns = [
    path("", views.home, name="home", distill_path=True),
    path("tree/", views.tree, name="tree", distill_path=True),
    path("tree/map/", views.family_map, name="map", distill_path=True),
    path("search/", views.search, name="search", distill_path=True),
    path("photos/who/", views.who_is_this, name="who", distill_path=True),
    path(
        "people/<slug:identifier>/",
        views.person_detail,
        name="person_detail",
        distill_path=True,
        distill_func=every_person,
    ),
    path(
        "recipes/<slug:slug>/",
        views.recipe_detail,
        name="recipe_detail",
        distill_path=True,
        distill_func=every_recipe,
    ),
]

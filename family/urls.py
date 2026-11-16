"""Pages of the site.

`distill_path=True` marks a page to be exported as a static file. Pages with a
parameter also say, in `distill_func`, which values exist (one page each).
"""
from django.urls import path

from . import views

app_name = "family"

urlpatterns = [
    path("", views.tree, name="tree", distill_path=True),
    path("people/", views.person_list, name="person_list", distill_path=True),
]

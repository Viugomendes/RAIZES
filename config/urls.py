"""Addresses of the project.

The admin panel has no language prefix and is never exported. The pages of
the site live under a language prefix: /pt-br/... and /es/...
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

from access import views as access_views
from family import views

urlpatterns = [
    path("admin/", admin.site.urls),
    # The view password: /entrar/ and /sair/, the same in every language.
    path("", include("access.urls")),
    path("robots.txt", access_views.robots, name="robots"),
    # The data the pages read in the browser (tree, search, mural, maps).
    path("data/family.js", views.family_data, name="family_data", distill_path=True),
    # Smaller copies of the photos, made on request while working locally.
    # The export writes the same files into dist/media/v/.
    re_path(r"^media/v/(?P<path>.+)$", views.media_variant, name="media_variant"),
    # Clips are the only media files sent as they are.
    re_path(
        r"^media/(?P<path>clips/.+)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
        name="media_clip",
    ),
]

urlpatterns += i18n_patterns(
    path("", include("family.urls")),
)

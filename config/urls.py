"""Addresses of the project.

The admin panel has no language prefix and is never exported. The pages of
the site live under a language prefix: /pt-br/... and /es/...
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.static import serve

from access import views as access_views
from access.admin_site import site as admin_site
from family import views

# The header of the panel on the password pages (no user is logged in there).
PANEL = {
    "site_header": admin_site.site_header,
    "site_title": admin_site.site_title,
    "site_url": None,
}

urlpatterns = [
    # Forgotten password of the panel: Django's views with the admin's templates.
    path(
        "painel/senha/",
        auth_views.PasswordResetView.as_view(extra_context=PANEL),
        name="admin_password_reset",
    ),
    path(
        "painel/senha/enviado/",
        auth_views.PasswordResetDoneView.as_view(extra_context=PANEL),
        name="password_reset_done",
    ),
    path(
        "painel/senha/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(extra_context=PANEL),
        name="password_reset_confirm",
    ),
    path(
        "painel/senha/pronto/",
        auth_views.PasswordResetCompleteView.as_view(extra_context=PANEL),
        name="password_reset_complete",
    ),
    path("painel/", admin_site.urls),
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

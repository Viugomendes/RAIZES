"""Addresses of the project.

The admin panel has no language prefix and is never exported. The pages of
the site live under a language prefix: /pt-br/... and /es/...
"""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
]

urlpatterns += i18n_patterns(
    path("", include("family.urls")),
)

# Photos are served by Django only while working locally.
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

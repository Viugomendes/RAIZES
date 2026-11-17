"""The project's addresses plus the static files, which the test client does not serve."""
from django.contrib.staticfiles.views import serve
from django.urls import re_path

from config.urls import urlpatterns as project_urlpatterns

urlpatterns = [
    *project_urlpatterns,
    re_path(r"^static/(?P<path>.*)$", serve, {"insecure": True}),
]

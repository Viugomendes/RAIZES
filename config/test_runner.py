"""Runs the tests with the view password switched off.

Most tests open pages as a visitor would; only the tests of the gate itself
turn it on, with @override_settings(RAIZES_VIEW_GATE=True).
"""
from django.conf import settings
from django.test.runner import DiscoverRunner


class RaizesTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.RAIZES_VIEW_GATE = False

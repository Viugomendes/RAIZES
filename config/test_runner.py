"""Runs the tests with the view password switched off.

Most tests open pages as a visitor would; only the tests of the gate itself
turn it on, with @override_settings(RAIZES_VIEW_GATE=True).
"""
from django.conf import settings
from django.contrib.auth.hashers import get_hashers, get_hashers_by_algorithm
from django.test.runner import DiscoverRunner


class RaizesTestRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        settings.RAIZES_VIEW_GATE = False
        # A fast hasher: the tests log in many times (no test checks the algorithm).
        settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
        get_hashers.cache_clear()
        get_hashers_by_algorithm.cache_clear()

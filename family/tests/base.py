"""Shared helpers of the tests."""
import tempfile
from pathlib import Path

from django.test import TestCase, override_settings

from family.demo import load_demo_family


class IsolatedFilesMixin:
    """Every file the tests write (photos, copies, history) goes to a
    temporary folder, never to demo/ or data/."""

    @classmethod
    def setUpClass(cls):
        cls._files = tempfile.TemporaryDirectory()
        root = Path(cls._files.name)
        cls._file_settings = override_settings(
            MEDIA_ROOT=root / "media",
            RAIZES_CACHE_DIR=root / "cache",
            RAIZES_HISTORY_FILE=root / "export-history.json",
        )
        cls._file_settings.enable()
        try:
            super().setUpClass()
        except Exception:
            cls._file_settings.disable()
            cls._files.cleanup()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls._file_settings.disable()
            cls._files.cleanup()


class DemoFamilyTestCase(IsolatedFilesMixin, TestCase):
    """Base class for tests that need the invented family loaded."""

    @classmethod
    def setUpTestData(cls):
        load_demo_family()

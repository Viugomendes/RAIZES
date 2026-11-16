#!/usr/bin/env python
"""Command-line entry point: every `python manage.py ...` command starts here."""
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django is not installed in this Python. Activate the virtual "
            "environment first (see README.md)."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

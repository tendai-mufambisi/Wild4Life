#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "w4l_donations.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and the "
            "virtual environment is activated?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

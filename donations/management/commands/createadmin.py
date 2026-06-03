"""
Management command: createadmin

Creates a Django superuser from environment variables so deployment pipelines
can bootstrap an admin account without an interactive shell session.

Required env vars:
  DJANGO_SUPERUSER_USERNAME
  DJANGO_SUPERUSER_EMAIL
  DJANGO_SUPERUSER_PASSWORD

Idempotent: if the username already exists the command exits cleanly.
"""

import os
import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_* environment variables (non-interactive)."

    def handle(self, *args, **options) -> None:  # noqa: ANN002, ANN003
        User = get_user_model()

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email    = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "").strip()

        missing = [
            name
            for name, val in [
                ("DJANGO_SUPERUSER_USERNAME", username),
                ("DJANGO_SUPERUSER_EMAIL", email),
                ("DJANGO_SUPERUSER_PASSWORD", password),
            ]
            if not val
        ]
        if missing:
            raise CommandError(
                f"Missing required environment variable(s): {', '.join(missing)}. "
                "Set them before running this command."
            )

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f"Superuser '{username}' already exists — skipping.")
            )
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully."))

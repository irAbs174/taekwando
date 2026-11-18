"""Synchronize TECHWANDO role groups and granular permissions."""
from django.core.management.base import BaseCommand

from apps.accounts.rbac import ensure_role_groups


class Command(BaseCommand):
    help = "Create or update all 5 TECHWANDO RBAC groups and their permissions."

    def handle(self, *args, **options):
        groups = ensure_role_groups()
        for name, grp in groups.items():
            self.stdout.write(
                self.style.SUCCESS(f"Role group '{name}' synced ({grp.permissions.count()} permissions).")
            )

"""Compile locale/<lang>/LC_MESSAGES/django.po files into binary .mo catalogs."""
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile Persian (fa) and Korean (ko) gettext .po catalogs to .mo files."

    def handle(self, *args, **options):
        compiled = 0
        for locale_root in settings.LOCALE_PATHS:
            root = Path(locale_root)
            for po_path in sorted(root.glob("*/LC_MESSAGES/*.po")):
                mo_path = po_path.with_suffix(".mo")
                po = polib.pofile(str(po_path), encoding="utf-8")
                po.save_as_mofile(str(mo_path))
                compiled += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Compiled {po_path.relative_to(settings.BASE_DIR)} -> "
                        f"{mo_path.relative_to(settings.BASE_DIR)} ({len(po)} entries)"
                    )
                )
        if compiled == 0:
            self.stdout.write(self.style.WARNING("No .po files found in LOCALE_PATHS."))

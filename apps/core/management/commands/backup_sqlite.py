"""Consistent, WAL-safe online SQLite backup command with integrity verification."""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a consistent online backup of the SQLite database with SHA-256 and integrity check."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=str(settings.BASE_DIR / "backups"),
            help="Directory to store backup snapshots (default: ./backups).",
        )
        parser.add_argument(
            "--keep",
            type=int,
            default=14,
            help="Maximum number of recent backups to retain (default: 14).",
        )

    def handle(self, *args, **options):
        db_cfg = settings.DATABASES["default"]
        if db_cfg["ENGINE"] != "django.db.backends.sqlite3":
            raise CommandError(
                "backup_sqlite only applies to SQLite databases. Use pg_dump for PostgreSQL."
            )

        src_path = Path(db_cfg["NAME"])
        if not src_path.is_file():
            raise CommandError(f"SQLite database file not found: {src_path}")

        out_dir = Path(options["output_dir"])
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        dest_path = out_dir / f"techwando_{stamp}.sqlite3"

        with sqlite3.connect(f"file:{src_path}?mode=ro", uri=True) as src_conn:
            with sqlite3.connect(str(dest_path)) as dst_conn:
                src_conn.backup(dst_conn)
                check = dst_conn.execute("PRAGMA integrity_check;").fetchone()
                if not check or check[0] != "ok":
                    dest_path.unlink(missing_ok=True)
                    raise CommandError(f"Backup integrity check failed: {check}")

        dest_path.chmod(0o600)
        digest = hashlib.sha256(dest_path.read_bytes()).hexdigest()
        sha_path = dest_path.with_suffix(".sqlite3.sha256")
        sha_path.write_text(f"{digest}  {dest_path.name}\n", encoding="utf-8")
        sha_path.chmod(0o600)

        keep = max(1, int(options["keep"]))
        snapshots = sorted(out_dir.glob("techwando_*.sqlite3"), reverse=True)
        for old in snapshots[keep:]:
            old.unlink(missing_ok=True)
            old.with_suffix(".sqlite3.sha256").unlink(missing_ok=True)

        self.stdout.write(
            self.style.SUCCESS(f"Verified SQLite backup saved: {dest_path} (sha256: {digest[:16]}...)")
        )

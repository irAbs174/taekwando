"""Security tests: protected private media, upload validation, XSS/SQLi, headers, and CLI commands."""
import datetime
import hashlib
import sqlite3
import tempfile
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings

from apps.accounts.models import UserRole
from apps.core.models import ApprovalStatus, Discipline
from apps.core.validators import (
    validate_safe_document as validate_document_upload,
    validate_safe_image as validate_image_upload,
)
from apps.medals.models import Medal, MedalType
from tests.base import TechwandoTestCase, make_pdf_upload, make_png_upload


class SecurityAndManagementCommandTests(TechwandoTestCase):
    def setUp(self):
        self.moderator = self.create_user("sec_mod@tw.test", role=UserRole.MODERATOR)
        self.owner_user, self.owner = self.create_member("owner@tw.test")
        self.intruder_user, self.intruder = self.create_member("intruder@tw.test")
        self.medal = Medal.objects.create(
            member=self.owner,
            medal_type=MedalType.GOLD,
            discipline=Discipline.TAEKWONDO,
            competition_name="جام بین‌المللی",
            award_date=datetime.date(2026, 4, 1),
            approval_status=ApprovalStatus.PENDING,
            evidence=make_pdf_upload("private_cert.pdf"),
        )

    def test_private_certificate_access_control_and_url_guessing_blocked(self):
        protected_url = self.medal.get_evidence_url()
        raw_filename = Path(self.medal.evidence.name).name

        # File is randomized (does NOT keep user-supplied filename) and stored outside MEDIA_ROOT
        self.assertNotIn("private_cert", raw_filename)
        self.assertFalse((self._media_root / self.medal.evidence.name).exists())
        self.assertTrue((self._private_root / self.medal.evidence.name).exists())

        # Direct /media/certificates/... and /media/medals/... guessing returns 403
        self.assertEqual(
            self.client.get(f"/media/{self.medal.evidence.name}").status_code, 403
        )
        self.assertEqual(self.client.get("/media/certificates/2026/04/guess.pdf").status_code, 403)

        # Unauthenticated redirected to login
        anon = self.client.get(protected_url)
        self.assertEqual(anon.status_code, 302)

        # Another member strictly receives 403 Forbidden
        self.client.force_login(self.intruder_user)
        self.assertEqual(self.client.get(protected_url).status_code, 403)

        # Owner receives 200 with strict private cache & nosniff headers
        self.client.force_login(self.owner_user)
        ok_owner = self.client.get(protected_url)
        self.assertEqual(ok_owner.status_code, 200)
        self.assertEqual(ok_owner["X-Content-Type-Options"], "nosniff")
        self.assertIn("no-store", ok_owner["Cache-Control"])
        if hasattr(ok_owner, "close"):
            ok_owner.close()

        # Authorized Moderator receives 200; verify X-Accel-Redirect mode for Nginx
        self.client.force_login(self.moderator)
        with override_settings(USE_X_ACCEL_REDIRECT=True, X_ACCEL_REDIRECT_PREFIX="/_private_media"):
            accel = self.client.get(protected_url)
            self.assertEqual(accel.status_code, 200)
            self.assertTrue(accel["X-Accel-Redirect"].startswith("/_private_media/medals/"))

    def test_file_upload_validators_reject_malicious_spoofed_and_oversized_files(self):
        # Valid image and PDF pass
        validate_image_upload(make_png_upload("ok.png"))
        validate_document_upload(make_pdf_upload("ok.pdf"))

        # Dangerous executable / script extensions rejected
        exe = SimpleUploadedFile("shell.php", b"<?php system($_GET['c']); ?>", content_type="application/x-php")
        with self.assertRaises(ValidationError):
            validate_document_upload(exe)

        # Extension spoofing (EXE bytes pretending to be .pdf or .png) rejected
        fake_pdf = SimpleUploadedFile("spoof.pdf", b"MZ\x90\x00not_a_pdf", content_type="application/pdf")
        with self.assertRaises(ValidationError):
            validate_document_upload(fake_pdf)

        fake_png = SimpleUploadedFile("spoof.png", b"not an image at all", content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_image_upload(fake_png)

        # PDF containing embedded JavaScript action rejected
        js_pdf = SimpleUploadedFile(
            "evil.pdf",
            b"%PDF-1.4\n1 0 obj << /S /JavaScript /JS (app.alert(1)) >> endobj\n%%EOF",
            content_type="application/pdf",
        )
        with self.assertRaises(ValidationError):
            validate_document_upload(js_pdf)

        # Oversized file rejected
        with override_settings(MAX_UPLOAD_SIZE_MB=1, MAX_UPLOAD_SIZE_BYTES=1024):
            big = SimpleUploadedFile("big.pdf", b"%PDF-1.4\n" + b"0" * 2048, content_type="application/pdf")
            with self.assertRaises(ValidationError):
                validate_document_upload(big)

    def test_xss_escaping_sqli_safety_and_security_headers(self):
        xss_payload = '<script>alert("xss")</script>'
        sqli_payload = "' OR 1=1 --"

        r_xss = self.client.get("/fa/champions/", {"q": xss_payload})
        self.assertEqual(r_xss.status_code, 200)
        body = r_xss.content.decode("utf-8")
        self.assertNotIn('<script>alert("xss")</script>', body)
        self.assertIn("&lt;script&gt;", body)

        # Security headers set by SecurityHeadersMiddleware + Django middleware
        self.assertEqual(r_xss["X-Frame-Options"], "DENY")
        self.assertEqual(r_xss["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", r_xss["Content-Security-Policy"])
        self.assertEqual(r_xss["Referrer-Policy"], "strict-origin-when-cross-origin")
        self.assertIn("camera=()", r_xss["Permissions-Policy"])

        # SQL injection payload handled safely via parameterized ORM queries
        r_sqli = self.client.get("/fa/champions/", {"q": sqli_payload})
        self.assertEqual(r_sqli.status_code, 200)

        # Health endpoint returns 200 JSON ok
        health = self.client.get("/healthz/")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")

    def test_seed_command_idempotency_and_sqlite_online_backup_verification(self):
        # Run seed twice to prove full idempotency
        call_command("seed_techwando", "--with-demo-accounts")
        call_command("seed_techwando", "--with-demo-accounts")
        self.assertEqual(self.client.get("/fa/").status_code, 200)
        self.assertEqual(self.client.get("/ko/").status_code, 200)

        # Test backup_sqlite against a real file-backed SQLite DB
        with tempfile.TemporaryDirectory() as tmp:
            src_db = Path(tmp) / "source.sqlite3"
            out_dir = Path(tmp) / "backups"
            conn = sqlite3.connect(src_db)
            conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
            conn.execute("INSERT INTO t (name) VALUES ('techwando')")
            conn.commit()
            conn.close()

            from django.conf import settings

            orig_name = settings.DATABASES["default"]["NAME"]
            settings.DATABASES["default"]["NAME"] = str(src_db)
            try:
                call_command("backup_sqlite", "--output-dir", str(out_dir), "--keep", "2")
            finally:
                settings.DATABASES["default"]["NAME"] = orig_name

            snaps = list(out_dir.glob("techwando_*.sqlite3"))
            self.assertEqual(len(snaps), 1)
            sha_file = Path(f"{snaps[0]}.sha256")
            self.assertTrue(sha_file.exists())
            expected_digest = sha_file.read_text().split()[0]
            actual_digest = hashlib.sha256(snaps[0].read_bytes()).hexdigest()
            self.assertEqual(expected_digest, actual_digest)

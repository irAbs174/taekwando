"""App-level audit log tests (full coverage in `tests/`)."""
from django.test import TestCase


class AuditLogAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.audit_logs.models import AuditLog

        self.assertEqual(AuditLog._meta.app_label, "audit_logs")

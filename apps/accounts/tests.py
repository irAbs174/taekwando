"""App-level placeholder (comprehensive auth/RBAC tests in `tests/`)."""
from django.test import TestCase


class AccountsAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.accounts.models import User

        self.assertEqual(User._meta.app_label, "accounts")

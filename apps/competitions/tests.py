"""App-level competition tests."""
from django.test import TestCase


class CompetitionsAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.competitions.models import Competition

        self.assertEqual(Competition._meta.app_label, "competitions")

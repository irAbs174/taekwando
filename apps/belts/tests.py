"""App-level belt tests."""
from django.test import TestCase


class BeltsAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.belts.models import BeltType

        self.assertEqual(BeltType._meta.app_label, "belts")

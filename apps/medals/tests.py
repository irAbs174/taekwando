"""App-level medals test."""
from django.test import TestCase


class MedalsAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.medals.models import Medal

        self.assertEqual(Medal._meta.app_label, "medals")

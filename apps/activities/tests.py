"""App-level activities test."""
from django.test import TestCase


class ActivitiesAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.activities.models import SocialActivity

        self.assertEqual(SocialActivity._meta.app_label, "activities")

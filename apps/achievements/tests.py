"""App-level achievements test."""
from django.test import TestCase


class AchievementsAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.achievements.models import Achievement

        self.assertEqual(Achievement._meta.app_label, "achievements")

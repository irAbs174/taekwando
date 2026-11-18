"""App-level notification tests."""
from django.test import TestCase


class NotificationAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.notifications.models import Notification

        self.assertEqual(Notification._meta.app_label, "notifications")

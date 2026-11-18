"""App-level contact test."""
from django.test import TestCase


class ContactAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.contact.models import ContactMessage

        self.assertEqual(ContactMessage._meta.app_label, "contact")

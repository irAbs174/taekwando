"""App-level pages test."""
from django.test import TestCase


class PagesAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.pages.models import Page

        self.assertEqual(Page._meta.app_label, "pages")

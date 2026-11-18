"""App-level SEO tests."""
from django.test import TestCase


class SeoAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.seo.models import SEOMetadata

        self.assertEqual(SEOMetadata._meta.app_label, "seo")

"""App-level API smoke test (comprehensive endpoint tests in `tests/test_api.py`)."""
from django.test import TestCase


class ApiAppConfigTest(TestCase):
    def test_api_schema_url_resolves(self):
        from django.urls import reverse

        self.assertEqual(reverse("api:schema"), "/api/v1/schema/")

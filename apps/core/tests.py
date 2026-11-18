"""App-level placeholder delegating to unified suite under `tests/`."""
from django.test import TestCase

from apps.core.templatetags.techwando_tags import persian_digits


class CoreUtilitiesSmokeTest(TestCase):
    def test_persian_digits_conversion(self):
        self.assertEqual(persian_digits("2026"), "۲۰۲۶")

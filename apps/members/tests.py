"""App-level placeholder (full member portal tests in `tests/`)."""
from django.test import TestCase


class MembersAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.members.models import MemberProfile

        self.assertEqual(MemberProfile._meta.app_label, "members")

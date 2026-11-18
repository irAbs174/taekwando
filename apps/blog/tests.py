"""App-level blog test."""
from django.test import TestCase


class BlogAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.blog.models import Post

        self.assertEqual(Post._meta.app_label, "blog")

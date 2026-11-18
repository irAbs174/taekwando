"""App-level products test."""
from django.test import TestCase


class ProductsAppConfigTest(TestCase):
    def test_app_loaded(self):
        from apps.products.models import Product

        self.assertEqual(Product._meta.app_label, "products")

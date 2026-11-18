"""Django Admin configuration for Products with inline translations and images."""
from django.contrib import admin

from apps.products.models import (
    Product,
    ProductCategory,
    ProductCategoryTranslation,
    ProductImage,
    ProductTranslation,
)


class ProductCategoryTranslationInline(admin.TabularInline):
    model = ProductCategoryTranslation
    extra = 1
    max_num = 2


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "localized_name", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("slug", "translations__name")
    inlines = [ProductCategoryTranslationInline]
    list_per_page = 25


class ProductTranslationInline(admin.StackedInline):
    model = ProductTranslation
    extra = 1
    max_num = 2


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "sku",
        "__str__",
        "category",
        "discipline",
        "price",
        "currency",
        "is_available",
        "status",
    )
    list_filter = ("status", "discipline", "category", "is_available", "is_featured")
    search_fields = ("sku", "slug", "translations__name", "translations__description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProductTranslationInline, ProductImageInline]
    list_per_page = 25

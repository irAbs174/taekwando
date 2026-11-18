"""Django Admin configuration for Blog with inline Persian/Japanese translations."""
from django.contrib import admin

from apps.blog.models import Category, CategoryTranslation, Post, PostTranslation, Tag


class CategoryTranslationInline(admin.TabularInline):
    model = CategoryTranslation
    extra = 1
    max_num = 2


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("slug", "localized_name", "display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("slug", "translations__name")
    inlines = [CategoryTranslationInline]
    list_per_page = 25


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_fa", "name_ja")
    search_fields = ("slug", "name_fa", "name_ja")
    list_per_page = 30


class PostTranslationInline(admin.StackedInline):
    model = PostTranslation
    extra = 1
    max_num = 2


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "__str__",
        "category",
        "author",
        "status",
        "is_featured",
        "published_at",
    )
    list_filter = ("status", "is_featured", "category", "published_at")
    search_fields = ("slug", "translations__title", "translations__excerpt")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("tags",)
    inlines = [PostTranslationInline]
    list_per_page = 25
    date_hierarchy = "published_at"

"""Django Admin configuration for Page with inline Persian/Korean translations."""
from django.contrib import admin

from apps.core.admin import SupportedTranslationInlineMixin

from apps.pages.models import Page, PageTranslation


class PageTranslationInline(SupportedTranslationInlineMixin, admin.StackedInline):
    model = PageTranslation
    extra = 1
    max_num = 2


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "slug",
        "__str__",
        "page_type",
        "status",
        "display_order",
        "show_in_footer",
        "updated_at",
    )
    list_filter = ("page_type", "status", "show_in_footer")
    search_fields = ("slug", "translations__title", "translations__body")
    readonly_fields = ("created_at", "updated_at")
    inlines = [PageTranslationInline]
    list_per_page = 25

"""Django Admin configuration for SEOMetadata with inline translations."""
from django.contrib import admin

from apps.seo.models import SEOMetadata, SEOTranslation


class SEOTranslationInline(admin.StackedInline):
    model = SEOTranslation
    extra = 1
    max_num = 2


@admin.register(SEOMetadata)
class SEOMetadataAdmin(admin.ModelAdmin):
    list_display = ("id", "route_key", "robots_index", "robots_follow", "updated_at")
    list_filter = ("robots_index", "robots_follow")
    search_fields = ("route_key", "translations__seo_title", "translations__seo_description")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SEOTranslationInline]
    list_per_page = 25

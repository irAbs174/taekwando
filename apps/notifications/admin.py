"""Django Admin configuration for Notification."""
from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    exclude = ('message_ja',)
    list_display = ("id", "recipient", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("recipient__email", "message", "message_ko")
    readonly_fields = ("created_at", "read_at")
    raw_id_fields = ("recipient",)
    list_per_page = 30

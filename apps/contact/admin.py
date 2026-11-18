"""Django Admin configuration for ContactMessage."""
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.contact.models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "name", "email", "language", "is_read", "submitted_at")
    list_filter = ("is_read", "language", "submitted_at")
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("name", "email", "subject", "message", "language", "ip_address", "submitted_at", "read_at")
    list_per_page = 30
    date_hierarchy = "submitted_at"
    actions = ["mark_selected_read", "mark_selected_unread"]

    @admin.action(description=_("Mark selected messages as read"))
    def mark_selected_read(self, request, queryset):
        count = queryset.update(is_read=True, read_at=timezone.now(), handled_by=request.user)
        self.message_user(request, _("%(count)d message(s) marked read.") % {"count": count}, messages.SUCCESS)

    @admin.action(description=_("Mark selected messages as unread"))
    def mark_selected_unread(self, request, queryset):
        count = queryset.update(is_read=False, read_at=None)
        self.message_user(request, _("%(count)d message(s) marked unread.") % {"count": count}, messages.SUCCESS)

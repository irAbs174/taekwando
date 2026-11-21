"""Django Admin configuration for moderated Achievements."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.achievements.models import Achievement
from apps.core.admin import ModeratedModelAdminMixin


@admin.register(Achievement)
class AchievementAdmin(ModeratedModelAdminMixin, admin.ModelAdmin):
    exclude = ('title_ja', 'description_ja')
    list_display = (
        "id",
        "title",
        "member",
        "discipline",
        "competition",
        "achievement_date",
        "approval_status",
        "certificate_link",
        "reviewer",
        "reviewed_at",
    )
    list_filter = ("approval_status", "discipline", "achievement_date", "competition")
    search_fields = (
        "title",
        "title_ko",
        "description",
        "member__first_name",
        "member__last_name",
        "member__membership_number",
    )
    readonly_fields = ModeratedModelAdminMixin.moderation_readonly_fields + ("certificate_link",)
    raw_id_fields = ("member", "competition")
    list_per_page = 25
    date_hierarchy = "achievement_date"

    @admin.display(description=_("Certificate"))
    def certificate_link(self, obj: Achievement):
        url = obj.get_certificate_url()
        if not url:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, _("View"))

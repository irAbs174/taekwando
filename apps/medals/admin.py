"""Django Admin configuration for moderated Medals."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.core.admin import ModeratedModelAdminMixin
from apps.medals.models import Medal


@admin.register(Medal)
class MedalAdmin(ModeratedModelAdminMixin, admin.ModelAdmin):
    exclude = ('competition_name_ja', 'competition_location_ja')
    list_display = (
        "id",
        "medal_type",
        "member",
        "discipline",
        "competition_name",
        "competition_location",
        "award_date",
        "approval_status",
        "evidence_link",
        "reviewer",
        "reviewed_at",
    )
    list_filter = ("approval_status", "medal_type", "discipline", "award_date", "competition")
    search_fields = (
        "competition_name",
        "competition_name_ko",
        "competition_location",
        "division_category",
        "member__first_name",
        "member__last_name",
        "member__membership_number",
    )
    readonly_fields = ModeratedModelAdminMixin.moderation_readonly_fields + ("evidence_link",)
    raw_id_fields = ("member", "competition")
    list_per_page = 25
    date_hierarchy = "award_date"

    @admin.display(description=_("Evidence"))
    def evidence_link(self, obj: Medal):
        url = obj.get_evidence_url()
        if not url:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, _("View"))

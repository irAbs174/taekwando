"""Django Admin configuration for BeltType and moderated BeltHistory."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.belts.models import BeltHistory, BeltType
from apps.core.admin import ModeratedModelAdminMixin


@admin.register(BeltType)
class BeltTypeAdmin(admin.ModelAdmin):
    exclude = ('name_ja',)
    list_display = (
        "discipline",
        "rank_order",
        "rank_code",
        "name_fa",
        "name_ko",
        "is_black_belt",
        "is_active",
    )
    list_filter = ("discipline", "is_black_belt", "is_active")
    search_fields = ("name_fa", "name_ko", "rank_code")
    list_per_page = 30


@admin.register(BeltHistory)
class BeltHistoryAdmin(ModeratedModelAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "member",
        "belt_type",
        "discipline",
        "award_date",
        "approval_status",
        "certificate_link",
        "reviewer",
        "reviewed_at",
    )
    list_filter = ("approval_status", "discipline", "belt_type", "award_date")
    search_fields = (
        "member__first_name",
        "member__last_name",
        "member__membership_number",
        "issuing_authority",
    )
    readonly_fields = ModeratedModelAdminMixin.moderation_readonly_fields + ("certificate_link",)
    raw_id_fields = ("member",)
    list_per_page = 25
    date_hierarchy = "award_date"

    @admin.display(description=_("Certificate"))
    def certificate_link(self, obj: BeltHistory):
        url = obj.get_certificate_url()
        if not url:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, _("View"))

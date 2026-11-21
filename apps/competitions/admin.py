"""Django Admin configuration for Competition and CompetitionParticipation."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.competitions.models import Competition, CompetitionParticipation
from apps.core.admin import ModeratedModelAdminMixin


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    exclude = ('title_ja', 'location_ja', 'organizer_ja', 'description_ja', 'results_summary_ja')
    list_display = (
        "title_fa",
        "title_ko",
        "discipline",
        "location_fa",
        "start_date",
        "end_date",
        "organizer",
        "is_published",
    )
    list_filter = ("discipline", "is_published", "start_date")
    search_fields = ("title_fa", "title_ko", "location_fa", "location_ko", "organizer", "slug")
    prepopulated_fields = {"slug": ("title_ko",)}
    list_per_page = 25
    date_hierarchy = "start_date"


@admin.register(CompetitionParticipation)
class CompetitionParticipationAdmin(ModeratedModelAdminMixin, admin.ModelAdmin):
    exclude = ('result_ja',)
    list_display = (
        "id",
        "member",
        "competition",
        "division_category",
        "result",
        "placement",
        "approval_status",
        "certificate_link",
        "reviewer",
    )
    list_filter = ("approval_status", "competition__discipline", "competition")
    search_fields = (
        "member__first_name",
        "member__last_name",
        "member__membership_number",
        "competition__title_fa",
        "competition__title_ko",
        "division_category",
        "result",
    )
    readonly_fields = ModeratedModelAdminMixin.moderation_readonly_fields + ("certificate_link",)
    raw_id_fields = ("member", "competition")
    list_per_page = 25

    @admin.display(description=_("Certificate"))
    def certificate_link(self, obj: CompetitionParticipation):
        url = obj.get_certificate_url()
        if not url:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, _("View"))

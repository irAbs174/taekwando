"""Django Admin configuration for moderated SocialActivity records."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.activities.models import SocialActivity
from apps.core.admin import ModeratedModelAdminMixin


@admin.register(SocialActivity)
class SocialActivityAdmin(ModeratedModelAdminMixin, admin.ModelAdmin):
    exclude = ('title_ja', 'description_ja', 'location_ja')
    list_display = (
        "id",
        "title",
        "member",
        "location",
        "activity_date",
        "public_visibility_consent",
        "approval_status",
        "photo_link",
        "reviewer",
        "reviewed_at",
    )
    list_filter = ("approval_status", "public_visibility_consent", "activity_date")
    search_fields = (
        "title",
        "title_ko",
        "location",
        "description",
        "member__first_name",
        "member__last_name",
        "member__membership_number",
    )
    readonly_fields = ModeratedModelAdminMixin.moderation_readonly_fields + ("photo_link",)
    raw_id_fields = ("member",)
    list_per_page = 25
    date_hierarchy = "activity_date"

    @admin.display(description=_("Photograph"))
    def photo_link(self, obj: SocialActivity):
        url = obj.get_private_photo_url()
        if not url:
            return "—"
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>', url, _("View"))

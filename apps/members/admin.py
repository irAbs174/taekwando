"""Django Admin configuration for MemberProfile with audited bulk approval."""
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from apps.core.permissions import can_manage_members
from apps.members.models import MemberProfile, MembershipStatus
from apps.members.services import review_membership_application


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = (
        "membership_number",
        "full_name",
        "user",
        "primary_discipline",
        "membership_status",
        "public_profile_consent",
        "public_profile_visibility",
        "joining_date",
    )
    list_filter = (
        "membership_status",
        "primary_discipline",
        "public_profile_consent",
        "public_profile_visibility",
        "joining_date",
    )
    search_fields = (
        "membership_number",
        "first_name",
        "last_name",
        "first_name_ja",
        "last_name_ja",
        "user__email",
        "phone",
    )
    readonly_fields = (
        "membership_number",
        "slug",
        "reviewer",
        "reviewed_at",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("user",)
    list_per_page = 25
    date_hierarchy = "joining_date"
    actions = ["approve_selected_memberships", "reject_selected_memberships"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_manage_members(request.user):
            actions.pop("approve_selected_memberships", None)
            actions.pop("reject_selected_memberships", None)
        return actions

    @admin.action(description=_("Approve selected membership applications"))
    def approve_selected_memberships(self, request, queryset):
        if not can_manage_members(request.user):
            raise PermissionDenied
        count = 0
        for profile in queryset.select_related("user"):
            if profile.user_id == request.user.id:
                continue
            review_membership_application(
                profile=profile,
                reviewer=request.user,
                new_status=MembershipStatus.APPROVED,
                note=profile.admin_note,
                request=request,
            )
            count += 1
        self.message_user(
            request,
            _("%(count)d membership application(s) approved.") % {"count": count},
            messages.SUCCESS,
        )

    @admin.action(description=_("Reject selected membership applications"))
    def reject_selected_memberships(self, request, queryset):
        if not can_manage_members(request.user):
            raise PermissionDenied
        count = 0
        for profile in queryset.select_related("user"):
            review_membership_application(
                profile=profile,
                reviewer=request.user,
                new_status=MembershipStatus.REJECTED,
                note=profile.admin_note or "Rejected via admin moderation.",
                request=request,
            )
            count += 1
        self.message_user(
            request,
            _("%(count)d membership application(s) rejected.") % {"count": count},
            messages.SUCCESS,
        )

    def save_model(self, request, obj, form, change):
        if change and "membership_status" in form.changed_data:
            desired_status = obj.membership_status
            desired_note = obj.admin_note
            prev = MemberProfile.objects.get(pk=obj.pk)
            obj.membership_status = prev.membership_status
            obj.admin_note = prev.admin_note
            super().save_model(request, obj, form, change)
            review_membership_application(
                profile=obj,
                reviewer=request.user,
                new_status=desired_status,
                note=desired_note,
                request=request,
            )
            return
        super().save_model(request, obj, form, change)

"""Django Admin branding and immutable ReviewLog administration."""
from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import ApprovalStatus, ReviewLog
from apps.core.permissions import can_moderate_submission
from apps.core.services import ModerationService

admin.site.site_header = _("TEAKWONDO Administration")
admin.site.site_title = _("TEAKWONDO Admin")
admin.site.index_title = _("Club, Athlete & Multilingual Content Management")


class ModeratedModelAdminMixin:
    """
    Reusable Django Admin mixin providing role-gated bulk moderation actions
    and automatic ReviewLog + AuditLog + Notification dispatch.
    """

    moderation_readonly_fields = ("reviewer", "reviewed_at", "created_at", "updated_at")
    actions = ["bulk_approve", "bulk_reject", "bulk_request_revision"]
    formfield_overrides = {
        models.FileField: {"widget": forms.FileInput},
        models.ImageField: {"widget": forms.FileInput},
    }

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not can_moderate_submission(request.user, self.model._meta.model_name):
            for key in ("bulk_approve", "bulk_reject", "bulk_request_revision"):
                actions.pop(key, None)
        return actions

    def _run_bulk_decision(self, request, queryset, status: str, default_note: str) -> None:
        if not can_moderate_submission(request.user, self.model._meta.model_name):
            raise PermissionDenied
        updated = 0
        skipped_self = 0
        for item in queryset.select_related("member", "member__user"):
            if item.member.user_id == request.user.id:
                skipped_self += 1
                continue
            ModerationService.review_submission(
                item,
                reviewer=request.user,
                new_status=status,
                note=item.admin_note or default_note,
                request=request,
            )
            updated += 1
        if updated:
            self.message_user(
                request,
                _("%(count)d submission(s) updated.") % {"count": updated},
                messages.SUCCESS,
            )
        if skipped_self:
            self.message_user(
                request,
                _("%(count)d own submission(s) skipped (self-approval forbidden).")
                % {"count": skipped_self},
                messages.WARNING,
            )

    @admin.action(description=_("Approve selected submissions"))
    def bulk_approve(self, request, queryset):
        self._run_bulk_decision(request, queryset, ApprovalStatus.APPROVED, "")

    @admin.action(description=_("Reject selected submissions"))
    def bulk_reject(self, request, queryset):
        self._run_bulk_decision(
            request,
            queryset,
            ApprovalStatus.REJECTED,
            "Rejected via admin bulk moderation.",
        )

    @admin.action(description=_("Request revision on selected submissions"))
    def bulk_request_revision(self, request, queryset):
        self._run_bulk_decision(
            request,
            queryset,
            ApprovalStatus.NEEDS_REVISION,
            "Please review and update supporting information.",
        )

    def save_model(self, request, obj, form, change):
        if change and ("approval_status" in form.changed_data or "admin_note" in form.changed_data):
            new_status = obj.approval_status
            new_note = obj.admin_note
            # Save any non-moderation fields first without altering persisted status
            original = self.model.objects.get(pk=obj.pk)
            obj.approval_status = original.approval_status
            obj.admin_note = original.admin_note
            obj.reviewer = original.reviewer
            obj.reviewed_at = original.reviewed_at
            super().save_model(request, obj, form, change)
            ModerationService.review_submission(
                obj,
                reviewer=request.user,
                new_status=new_status,
                note=new_note,
                request=request,
            )
            return
        super().save_model(request, obj, form, change)


@admin.register(ReviewLog)
class ReviewLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "target_repr",
        "content_type",
        "event_type",
        "previous_status",
        "new_status",
        "reviewer",
        "created_at",
    )
    list_filter = ("event_type", "new_status", "content_type", "created_at")
    search_fields = ("target_repr", "note", "reviewer__email")
    readonly_fields = (
        "content_type",
        "object_id",
        "target_repr",
        "event_type",
        "previous_status",
        "new_status",
        "reviewer",
        "note",
        "created_at",
    )
    list_per_page = 30
    date_hierarchy = "created_at"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class SupportedTranslationInlineMixin:
    """Keep historical translations without exposing them in supported-language forms."""

    def get_queryset(self, request):
        from apps.core.translation_utils import SUPPORTED_LANGUAGES

        return super().get_queryset(request).filter(language__in=SUPPORTED_LANGUAGES)

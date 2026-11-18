"""Read-only Django Admin interface for AuditLog (restricted to Super Admins & Managers)."""
from django.contrib import admin

from apps.audit_logs.models import AuditLog
from apps.core.permissions import user_has_any_role


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "actor_email",
        "action",
        "target_model",
        "target_id",
        "target_repr",
        "ip_address",
    )
    list_filter = ("action", "target_model", "created_at")
    search_fields = ("actor_email", "action", "target_model", "target_id", "target_repr", "ip_address")
    readonly_fields = (
        "actor",
        "actor_email",
        "action",
        "target_model",
        "target_id",
        "target_repr",
        "previous_state",
        "new_state",
        "ip_address",
        "user_agent",
        "created_at",
    )
    list_per_page = 40
    date_hierarchy = "created_at"

    def has_module_permission(self, request) -> bool:
        return user_has_any_role(request.user, {"SUPER_ADMIN", "CLUB_MANAGER"})

    def has_view_permission(self, request, obj=None) -> bool:
        return user_has_any_role(request.user, {"SUPER_ADMIN", "CLUB_MANAGER"})

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

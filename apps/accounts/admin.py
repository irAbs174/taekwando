"""Customized Django Admin configuration for the TECHWANDO User model."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserRole
from apps.accounts.rbac import sync_user_role_group
from apps.audit_logs.services import log_audit_event
from apps.members.models import MemberProfile


class MemberProfileInline(admin.StackedInline):
    model = MemberProfile
    fk_name = "user"
    can_delete = False
    extra = 0
    readonly_fields = ("membership_number", "slug", "reviewer", "reviewed_at")


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("-date_joined",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "preferred_language",
        "is_active",
        "is_staff",
        "date_joined",
    )
    list_filter = ("role", "is_active", "is_staff", "preferred_language", "date_joined")
    search_fields = ("email", "first_name", "last_name")
    readonly_fields = ("date_joined", "updated_at", "last_login")
    list_per_page = 25
    inlines = [MemberProfileInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal Info"),
            {"fields": ("first_name", "last_name", "preferred_language")},
        ),
        (
            _("Role & Access Control"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Timestamps"), {"fields": ("last_login", "date_joined", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "preferred_language",
                    "password1",
                    "password2",
                    "is_active",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and request.user.role != UserRole.SUPER_ADMIN:
            ro.extend(["role", "is_staff", "is_superuser", "groups", "user_permissions"])
        return tuple(ro)

    def save_model(self, request, obj: User, form, change):
        if not request.user.is_superuser and request.user.role != UserRole.SUPER_ADMIN:
            if not change:
                obj.role = UserRole.MEMBER
                obj.is_staff = False
                obj.is_superuser = False
            elif "role" in form.changed_data or "is_superuser" in form.changed_data:
                raise PermissionDenied
        super().save_model(request, obj, form, change)
        sync_user_role_group(obj)
        log_audit_event(
            actor=request.user,
            action="DJANGO_ADMIN_USER_UPDATED" if change else "DJANGO_ADMIN_USER_CREATED",
            instance=obj,
            new_state={"role": obj.role, "is_active": obj.is_active},
            request=request,
        )

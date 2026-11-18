"""DRF permission classes mirroring server-side RBAC and privacy rules."""
from rest_framework.permissions import BasePermission

from apps.core.permissions import (
    can_manage_content,
    can_manage_members,
    can_moderate_submission,
)


class IsActiveAuthenticated(BasePermission):
    def has_permission(self, request, view) -> bool:
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class IsClubManagerAPI(BasePermission):
    def has_permission(self, request, view) -> bool:
        return can_manage_members(request.user)


class IsContentAdminAPI(BasePermission):
    def has_permission(self, request, view) -> bool:
        return can_manage_content(request.user)


class IsSubmissionModeratorAPI(BasePermission):
    def has_permission(self, request, view) -> bool:
        model_key = getattr(view, "moderation_model_key", "")
        if not model_key:
            return False
        return can_moderate_submission(request.user, model_key)


class IsOwnMemberObject(BasePermission):
    def has_object_permission(self, request, view, obj) -> bool:
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        member = getattr(obj, "member", None)
        if member is not None:
            return member.user_id == request.user.id
        recipient_id = getattr(obj, "recipient_id", None)
        if recipient_id is not None:
            return recipient_id == request.user.id
        return False

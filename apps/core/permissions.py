"""Reusable RBAC permission mixins and server-side authorization helpers."""
from __future__ import annotations

from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied


def user_has_any_role(user, roles: set[str] | tuple[str, ...]) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.role == "SUPER_ADMIN":
        return True
    return user.role in set(roles)


def can_access_admin_portal(user) -> bool:
    return user_has_any_role(
        user,
        {"SUPER_ADMIN", "CONTENT_ADMIN", "CLUB_MANAGER", "MODERATOR"},
    )


def can_manage_members(user) -> bool:
    return user_has_any_role(user, {"SUPER_ADMIN", "CLUB_MANAGER"})


def can_manage_content(user) -> bool:
    return user_has_any_role(user, {"SUPER_ADMIN", "CONTENT_ADMIN"})


def can_moderate_submission(user, model_name: str) -> bool:
    """
    Granular server-side moderation permission check combining role + Django perms.
    - SUPER_ADMIN: all submissions
    - CLUB_MANAGER: memberships, medals, achievements, belts, competitions, activities
    - MODERATOR: social activities, achievements, medals, belts, competitions
      (when granted group/user permission; NOT user deletion or membership creation)
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.role == "SUPER_ADMIN":
        return True

    model_key = model_name.lower()
    if model_key == "memberprofile":
        return user.role == "CLUB_MANAGER" and user.has_perm("members.change_memberprofile")

    perm_map = {
        "medal": "medals.moderate_medal",
        "achievement": "achievements.moderate_achievement",
        "belthistory": "belts.moderate_belthistory",
        "socialactivity": "activities.moderate_socialactivity",
        "competitionparticipation": "competitions.moderate_competitionparticipation",
    }
    required_perm = perm_map.get(model_key)
    if user.role in {"CLUB_MANAGER", "MODERATOR"}:
        if required_perm:
            return user.has_perm(required_perm)
        return True
    return False


def can_view_private_submission_file(user, submission) -> bool:
    """
    Only the submission's owning member or an authorized moderator/manager/super-admin
    may view sensitive certificates, medal evidence, or unapproved activity files.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    member = getattr(submission, "member", None)
    if member is not None and member.user_id == user.id:
        return True
    return can_moderate_submission(user, submission._meta.model_name)


class RoleRequiredMixin(LoginRequiredMixin, AccessMixin):
    """CBV mixin enforcing active authentication and required role membership."""

    allowed_roles: tuple[str, ...] = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            return self.handle_no_permission()
        if not user_has_any_role(request.user, self.allowed_roles):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class MemberRequiredMixin(LoginRequiredMixin):
    """
    Ensures the user is authenticated, active, and owns a MemberProfile.
    Automatically scopes queries via `self.member_profile` — never trusts URL IDs
    for member identity.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_active:
            return self.handle_no_permission()
        from apps.members.services import ensure_member_profile

        self.member_profile = ensure_member_profile(request.user)
        return super().dispatch(request, *args, **kwargs)


class AdminPortalMixin(RoleRequiredMixin):
    allowed_roles = ("SUPER_ADMIN", "CONTENT_ADMIN", "CLUB_MANAGER", "MODERATOR")


class ClubManagerMixin(RoleRequiredMixin):
    allowed_roles = ("SUPER_ADMIN", "CLUB_MANAGER")


class ContentAdminMixin(RoleRequiredMixin):
    allowed_roles = ("SUPER_ADMIN", "CONTENT_ADMIN")


class ModeratorMixin(RoleRequiredMixin):
    allowed_roles = ("SUPER_ADMIN", "CLUB_MANAGER", "MODERATOR")

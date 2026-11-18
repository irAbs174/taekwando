"""Member object-level permission helpers."""
from apps.core.permissions import (  # noqa: F401
    ClubManagerMixin,
    MemberRequiredMixin,
    can_manage_members,
)


def can_view_member_private_profile(user, profile) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if profile.user_id == user.id:
        return True
    return can_manage_members(user)

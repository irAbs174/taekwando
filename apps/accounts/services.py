"""Transactional business logic for registration, user management, and roles."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserRole
from apps.accounts.rbac import sync_user_role_group
from apps.audit_logs.services import log_audit_event
from apps.core.translation_utils import normalize_lang
from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService


class AccountService:
    @staticmethod
    @transaction.atomic
    def register_public_member(
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone: str = "",
        primary_discipline: str = "TAEKWONDO",
        preferred_language: str | None = None,
        request=None,
    ) -> User:
        """
        Register a new club member safely.
        Role is ALWAYS hardcoded to UserRole.MEMBER — client input can NEVER
        grant administrative privileges.
        """
        from apps.members.services import create_member_profile_with_application

        lang = normalize_lang(preferred_language)
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=UserRole.MEMBER,
            preferred_language=lang,
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        profile = create_member_profile_with_application(
            user=user,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=phone.strip(),
            primary_discipline=primary_discipline,
            request=request,
        )

        log_audit_event(
            actor=user,
            action="MEMBER_REGISTERED",
            instance=user,
            new_state={
                "email": user.email,
                "role": user.role,
                "membership_number": profile.membership_number,
                "membership_status": profile.membership_status,
            },
            request=request,
        )

        NotificationService.notify_roles(
            roles=[UserRole.SUPER_ADMIN, UserRole.CLUB_MANAGER],
            message_fa=(
                f"درخواست عضویت جدید از {profile.full_name} "
                f"(شماره {profile.membership_number}) ثبت شد."
            ),
            message_ja=(
                f"{profile.full_name} さん（会員番号 {profile.membership_number}）から"
                f"新規入会申請が届きました。"
            ),
            notification_type=NotificationType.MEMBERSHIP_UPDATE,
            target_url=reverse("accounts:admin_member_detail", kwargs={"pk": profile.pk}),
        )

        NotificationService.notify_user(
            recipient=user,
            message_fa=(
                f"به باشگاه تکواندو خوش آمدید! شماره عضویت شما {profile.membership_number} است. "
                f"درخواست عضویت شما در انتظار تأیید مدیریت می‌باشد."
            ),
            message_ja=(
                f"TECHWANDOへようこそ！あなたの会員番号は {profile.membership_number} です。"
                f"現在、入会申請は管理者の承認待ちです。"
            ),
            notification_type=NotificationType.MEMBERSHIP_UPDATE,
            target_url=reverse("members:dashboard"),
        )
        return user

    @staticmethod
    @transaction.atomic
    def create_user_by_admin(
        *,
        actor: User,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role: str = UserRole.MEMBER,
        phone: str = "",
        primary_discipline: str = "TAEKWONDO",
        approve_immediately: bool = True,
        request=None,
    ) -> User:
        """Create a member (or staff user if actor is SUPER_ADMIN) with full auditing."""
        from apps.members.models import MembershipStatus
        from apps.members.services import create_member_profile_with_application

        if not (actor.is_superuser or actor.role in {UserRole.SUPER_ADMIN, UserRole.CLUB_MANAGER}):
            raise PermissionDenied

        # Club managers can ONLY create MEMBER accounts, never admin roles.
        if role != UserRole.MEMBER and not (
            actor.is_superuser or actor.role == UserRole.SUPER_ADMIN
        ):
            raise PermissionDenied(_("Only a Super Administrator can assign administrative roles."))

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            role=role,
            is_active=True,
        )
        initial_status = (
            MembershipStatus.APPROVED if approve_immediately else MembershipStatus.PENDING
        )
        profile = create_member_profile_with_application(
            user=user,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone=phone.strip(),
            primary_discipline=primary_discipline,
            initial_status=initial_status,
            actor=actor,
            request=request,
        )

        log_audit_event(
            actor=actor,
            action="ADMIN_CREATED_USER",
            instance=user,
            new_state={
                "email": user.email,
                "role": user.role,
                "membership_number": profile.membership_number,
                "membership_status": profile.membership_status,
            },
            request=request,
        )
        return user

    @staticmethod
    @transaction.atomic
    def change_user_role(*, actor: User, target_user: User, new_role: str, request=None) -> User:
        if not (actor.is_superuser or actor.role == UserRole.SUPER_ADMIN):
            raise PermissionDenied(_("Only Super Administrators can modify user roles."))
        if new_role not in dict(UserRole.choices):
            raise ValidationError(_("Invalid role selected."))
        if actor.id == target_user.id and new_role != UserRole.SUPER_ADMIN:
            raise ValidationError(_("You cannot downgrade your own Super Administrator role."))

        old_role = target_user.role
        if old_role == new_role:
            return target_user

        target_user.role = new_role
        target_user.save()
        sync_user_role_group(target_user)

        log_audit_event(
            actor=actor,
            action="USER_ROLE_CHANGED",
            instance=target_user,
            previous_state={"role": old_role},
            new_state={"role": new_role},
            request=request,
        )
        return target_user

    @staticmethod
    @transaction.atomic
    def set_user_active_status(
        *,
        actor: User,
        target_user: User,
        is_active: bool,
        request=None,
    ) -> User:
        if not (actor.is_superuser or actor.role in {UserRole.SUPER_ADMIN, UserRole.CLUB_MANAGER}):
            raise PermissionDenied
        if actor.id == target_user.id and not is_active:
            raise ValidationError(_("You cannot deactivate your own account."))
        if target_user.role != UserRole.MEMBER and not (
            actor.is_superuser or actor.role == UserRole.SUPER_ADMIN
        ):
            raise PermissionDenied(
                _("Only Super Administrators can activate or deactivate staff accounts.")
            )

        prev = target_user.is_active
        target_user.is_active = is_active
        target_user.save(update_fields=["is_active", "updated_at"])

        log_audit_event(
            actor=actor,
            action="USER_ACTIVATED" if is_active else "USER_DEACTIVATED",
            instance=target_user,
            previous_state={"is_active": prev},
            new_state={"is_active": is_active},
            request=request,
        )
        return target_user

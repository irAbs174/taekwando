"""Notification creation and read-state management services."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.core.permissions import can_moderate_submission
from apps.notifications.models import Notification, NotificationType


class NotificationService:
    @staticmethod
    def notify_user(
        *,
        recipient,
        message_fa: str,
        message_ko: str = "",
        notification_type: str = NotificationType.SYSTEM,
        target_url: str = "",
    ) -> Notification | None:
        if not recipient or not recipient.is_active:
            return None
        return Notification.objects.create(
            recipient=recipient,
            message=message_fa,
            message_ko=message_ko or message_fa,
            notification_type=notification_type,
            target_url=target_url[:255],
        )

    @staticmethod
    def notify_moderators(
        *,
        model_key: str,
        message_fa: str,
        message_ko: str = "",
        notification_type: str = NotificationType.SUBMISSION_PENDING,
        target_url: str = "",
        exclude_user_id: int | None = None,
    ) -> int:
        User = get_user_model()
        candidates = User.objects.filter(
            is_active=True,
            role__in=["SUPER_ADMIN", "CLUB_MANAGER", "MODERATOR"],
        )
        if exclude_user_id is not None:
            candidates = candidates.exclude(pk=exclude_user_id)

        to_create: list[Notification] = []
        for admin_user in candidates:
            if can_moderate_submission(admin_user, model_key):
                to_create.append(
                    Notification(
                        recipient=admin_user,
                        message=message_fa,
                        message_ko=message_ko or message_fa,
                        notification_type=notification_type,
                        target_url=target_url[:255],
                    )
                )
        if to_create:
            Notification.objects.bulk_create(to_create)
        return len(to_create)

    @staticmethod
    def notify_roles(
        *,
        roles: list[str],
        message_fa: str,
        message_ko: str = "",
        notification_type: str = NotificationType.SYSTEM,
        target_url: str = "",
    ) -> int:
        User = get_user_model()
        recipients = User.objects.filter(is_active=True, role__in=roles)
        items = [
            Notification(
                recipient=u,
                message=message_fa,
                message_ko=message_ko or message_fa,
                notification_type=notification_type,
                target_url=target_url[:255],
            )
            for u in recipients
        ]
        if items:
            Notification.objects.bulk_create(items)
        return len(items)

    @staticmethod
    def mark_as_read(notification: Notification, user) -> Notification:
        if notification.recipient_id != user.id:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])
        return notification

    @staticmethod
    def mark_all_as_read(user) -> int:
        return Notification.objects.filter(recipient=user, is_read=False).update(
            is_read=True,
            read_at=timezone.now(),
        )

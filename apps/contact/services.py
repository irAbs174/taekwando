"""Transactional contact message submission and admin review services."""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import UserRole
from apps.audit_logs.services import log_audit_event
from apps.contact.models import ContactMessage
from apps.core.security import get_client_ip, is_rate_limited, record_rate_limit_hit
from apps.core.translation_utils import normalize_lang
from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService


class ContactService:
    @staticmethod
    @transaction.atomic
    def submit_message(
        *,
        name: str,
        email: str,
        subject: str,
        message: str,
        language: str | None = None,
        request=None,
    ) -> ContactMessage:
        ip = get_client_ip(request)
        if ip:
            max_hits = getattr(settings, "CONTACT_RATE_LIMIT_ATTEMPTS", 5)
            window = getattr(settings, "CONTACT_RATE_LIMIT_WINDOW", 600)
            if is_rate_limited("contact", ip, max_hits, window):
                raise ValidationError(
                    _("Too many messages submitted recently. Please try again in a few minutes.")
                )
            record_rate_limit_hit("contact", ip, window)

        lang = normalize_lang(language)
        entry = ContactMessage.objects.create(
            name=name.strip(),
            email=email.strip().lower(),
            subject=subject.strip(),
            message=message.strip(),
            language=lang,
            ip_address=ip,
        )

        NotificationService.notify_roles(
            roles=[UserRole.SUPER_ADMIN, UserRole.CLUB_MANAGER, UserRole.CONTENT_ADMIN],
            message_fa=f"پیام تماس جدید از {entry.name}: «{entry.subject}»",
            message_ja=f"{entry.name} 様から新しいお問い合わせ：「{entry.subject}」",
            notification_type=NotificationType.CONTACT_MESSAGE,
            target_url=reverse("contact:admin_detail", kwargs={"pk": entry.pk}),
        )
        return entry

    @staticmethod
    @transaction.atomic
    def mark_reviewed(
        entry: ContactMessage,
        *,
        actor,
        is_read: bool = True,
        internal_note: str | None = None,
        request=None,
    ) -> ContactMessage:
        prev = {"is_read": entry.is_read, "internal_note": entry.internal_note}
        entry.is_read = is_read
        entry.read_at = timezone.now() if is_read else None
        entry.handled_by = actor
        if internal_note is not None:
            entry.internal_note = internal_note.strip()
        entry.save(update_fields=["is_read", "read_at", "handled_by", "internal_note"])
        log_audit_event(
            actor=actor,
            action="CONTACT_MESSAGE_REVIEWED",
            instance=entry,
            previous_state=prev,
            new_state={"is_read": entry.is_read, "internal_note": entry.internal_note},
            request=request,
        )
        return entry

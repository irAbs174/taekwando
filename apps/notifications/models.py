"""Notification model storing localized messages, type, target link, and read status."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.translation_utils import normalize_lang


class NotificationType(models.TextChoices):
    SUBMISSION_PENDING = "SUBMISSION_PENDING", _("Submission Pending")
    SUBMISSION_APPROVED = "SUBMISSION_APPROVED", _("Submission Approved")
    SUBMISSION_REJECTED = "SUBMISSION_REJECTED", _("Submission Rejected")
    SUBMISSION_REVISION = "SUBMISSION_REVISION", _("Revision Requested")
    CORRECTION_REQUEST = "CORRECTION_REQUEST", _("Correction Requested")
    MEMBERSHIP_UPDATE = "MEMBERSHIP_UPDATE", _("Membership Status Update")
    CONTACT_MESSAGE = "CONTACT_MESSAGE", _("New Contact Message")
    SYSTEM = "SYSTEM", _("System Notification")


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Recipient"),
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    message = models.TextField(_("Message (Persian / default)"))
    message_ja = models.TextField(_("Message (Japanese)"), blank=True)
    notification_type = models.CharField(
        _("Notification type"),
        max_length=32,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    target_url = models.CharField(_("Target link"), max_length=255, blank=True)
    is_read = models.BooleanField(_("Read status"), default=False, db_index=True)
    read_at = models.DateTimeField(_("Read at"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="notif_recipient_unread_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"To {self.recipient_id}: {self.localized_message[:60]}"

    @property
    def localized_message(self) -> str:
        if normalize_lang() == "ja" and self.message_ja:
            return self.message_ja
        return self.message

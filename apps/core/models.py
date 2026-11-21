"""Core abstract models, shared choices, and ReviewLog for the moderation workflow."""
from __future__ import annotations

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


class LanguageChoice(models.TextChoices):
    PERSIAN = "fa", _("Persian (fa-IR)")
    KOREAN = "ko", _("Korean (ko-KR)")


class ApprovalStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Review")
    APPROVED = "APPROVED", _("Approved")
    REJECTED = "REJECTED", _("Rejected")
    NEEDS_REVISION = "NEEDS_REVISION", _("Needs Revision")


class PublicationStatus(models.TextChoices):
    DRAFT = "DRAFT", _("Draft")
    SCHEDULED = "SCHEDULED", _("Scheduled")
    PUBLISHED = "PUBLISHED", _("Published")
    ARCHIVED = "ARCHIVED", _("Archived")


class Discipline(models.TextChoices):
    TAEKWONDO = "TAEKWONDO", _("Taekwondo")
    KARATE = "KARATE", _("Karate")
    JUDO = "JUDO", _("Judo")
    AIKIDO = "AIKIDO", _("Aikido")
    KENDO = "KENDO", _("Kendo")
    HAPKIDO = "HAPKIDO", _("Hapkido")
    OTHER = "OTHER", _("Other Martial Art")


class TimeStampedModel(models.Model):
    """Abstract base model providing indexed creation and update timestamps."""

    created_at = models.DateTimeField(_("Created at"), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        abstract = True


class ModeratedSubmissionModel(TimeStampedModel):
    """
    Reusable abstract base model for member submissions subject to administrator
    moderation (medals, achievements, belt promotions, social activities,
    competition records).
    """

    approval_status = models.CharField(
        _("Approval status"),
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    admin_note = models.TextField(_("Administrator feedback"), blank=True)
    correction_request = models.TextField(_("Member correction request"), blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Reviewer"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_%(app_label)s_%(class)s_set",
    )
    reviewed_at = models.DateTimeField(_("Review date"), null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def is_approved(self) -> bool:
        return self.approval_status == ApprovalStatus.APPROVED

    @property
    def is_pending(self) -> bool:
        return self.approval_status == ApprovalStatus.PENDING

    @property
    def can_member_edit(self) -> bool:
        """Members can directly edit PENDING or NEEDS_REVISION records."""
        return self.approval_status in {
            ApprovalStatus.PENDING,
            ApprovalStatus.NEEDS_REVISION,
        }

    @property
    def can_member_delete(self) -> bool:
        """Members can only delete unapproved PENDING or REJECTED submissions."""
        return self.approval_status in {
            ApprovalStatus.PENDING,
            ApprovalStatus.REJECTED,
            ApprovalStatus.NEEDS_REVISION,
        }

    @property
    def can_request_correction(self) -> bool:
        """Members can request corrections on APPROVED or REJECTED records."""
        return self.approval_status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
        }


class ReviewLog(models.Model):
    """
    Immutable moderation decision log attached to any moderated model
    (medals, achievements, belts, activities, competition records, memberships).
    """

    class EventType(models.TextChoices):
        SUBMITTED = "SUBMITTED", _("Submitted")
        RESUBMITTED = "RESUBMITTED", _("Resubmitted")
        CORRECTION_REQUESTED = "CORRECTION_REQUESTED", _("Correction Requested")
        REVIEWED = "REVIEWED", _("Reviewed")

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Target model"),
    )
    object_id = models.PositiveBigIntegerField(_("Target ID"))
    content_object = GenericForeignKey("content_type", "object_id")

    target_repr = models.CharField(_("Submission summary"), max_length=255)
    event_type = models.CharField(
        _("Event type"),
        max_length=25,
        choices=EventType.choices,
        default=EventType.REVIEWED,
    )
    previous_status = models.CharField(
        _("Previous status"),
        max_length=25,
        blank=True,
    )
    new_status = models.CharField(
        _("New status"),
        max_length=25,
        db_index=True,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Actor / Reviewer"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_logs",
    )
    note = models.TextField(_("Decision note"), blank=True)
    created_at = models.DateTimeField(_("Recorded at"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Review log")
        verbose_name_plural = _("Review logs")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["content_type", "object_id"], name="reviewlog_target_idx"),
            models.Index(fields=["-created_at"], name="reviewlog_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.target_repr}: {self.previous_status or 'NEW'} -> {self.new_status}"

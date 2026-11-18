"""Achievement model with private certificate storage and moderation status."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.competitions.models import Competition
from apps.core.models import ApprovalStatus, Discipline, ModeratedSubmissionModel
from apps.core.storage import private_media_storage, upload_private_certificate
from apps.core.translation_utils import normalize_lang
from apps.core.validators import validate_safe_document
from apps.members.models import MemberProfile


class AchievementQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(approval_status=ApprovalStatus.APPROVED)

    def publicly_visible(self):
        return self.filter(
            approval_status=ApprovalStatus.APPROVED,
            member__user__is_active=True,
            member__membership_status="APPROVED",
            member__public_profile_consent=True,
            member__public_profile_visibility=True,
        )


class Achievement(ModeratedSubmissionModel):
    member = models.ForeignKey(
        MemberProfile,
        verbose_name=_("Member"),
        on_delete=models.CASCADE,
        related_name="achievements",
    )
    title = models.CharField(_("Achievement title"), max_length=200)
    title_ja = models.CharField(_("Achievement title (Japanese)"), max_length=200, blank=True)
    description = models.TextField(_("Description"), blank=True, max_length=3000)
    description_ja = models.TextField(
        _("Description (Japanese)"),
        blank=True,
        max_length=3000,
    )
    discipline = models.CharField(
        _("Martial arts discipline"),
        max_length=20,
        choices=Discipline.choices,
        default=Discipline.TAEKWONDO,
        db_index=True,
    )
    competition = models.ForeignKey(
        Competition,
        verbose_name=_("Competition"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="achievements",
    )
    achievement_date = models.DateField(_("Achievement date"), db_index=True)
    certificate = models.FileField(
        _("Supporting certificate"),
        storage=private_media_storage,
        upload_to=upload_private_certificate,
        validators=[validate_safe_document],
        blank=True,
    )

    objects = AchievementQuerySet.as_manager()

    class Meta:
        verbose_name = _("Achievement")
        verbose_name_plural = _("Achievements")
        ordering = ["-achievement_date", "-id"]
        permissions = [
            ("moderate_achievement", "Can moderate achievement submissions"),
        ]
        indexes = [
            models.Index(
                fields=["member", "approval_status"],
                name="ach_member_status_idx",
            ),
            models.Index(
                fields=["approval_status", "-achievement_date"],
                name="ach_status_date_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.achievement_date and self.achievement_date > timezone.localdate():
            raise ValidationError(
                {"achievement_date": _("Achievement date cannot be in the future.")}
            )

    def __str__(self) -> str:
        return self.localized_title

    @property
    def localized_title(self) -> str:
        if normalize_lang() == "ja":
            return self.title_ja or self.title
        return self.title or self.title_ja

    @property
    def localized_description(self) -> str:
        if normalize_lang() == "ja":
            return self.description_ja or self.description
        return self.description or self.description_ja

    def get_member_url(self) -> str:
        return reverse("achievements:member_detail", kwargs={"pk": self.pk})

    def get_certificate_url(self) -> str:
        if not self.certificate:
            return ""
        return reverse(
            "core:protected_file",
            kwargs={"model_type": "achievement", "pk": self.pk},
        )

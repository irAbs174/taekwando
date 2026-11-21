"""BeltType and moderated BeltHistory models."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    ApprovalStatus,
    Discipline,
    ModeratedSubmissionModel,
    TimeStampedModel,
)
from apps.core.storage import private_media_storage, upload_private_certificate
from apps.core.translation_utils import normalize_lang
from apps.core.validators import validate_safe_document
from apps.members.models import MemberProfile


class BeltType(TimeStampedModel):
    """Canonical belt rank definition per martial arts discipline."""

    discipline = models.CharField(
        _("Martial arts discipline"),
        max_length=20,
        choices=Discipline.choices,
        default=Discipline.TAEKWONDO,
        db_index=True,
    )
    name_fa = models.CharField(_("Belt rank name (Persian)"), max_length=100)
    name_ko = models.CharField(_("Belt rank name (Korean)"), max_length=100, blank=True)

    # Legacy Korean data is retained but not used for Korean.
    name_ja = models.CharField(_("Belt rank name (Japanese)"), max_length=100)
    rank_code = models.CharField(
        _("Rank code"),
        max_length=40,
        help_text=_("Example: 10-GEUP, 5-GEUP, 1-DAN, 3-DAN"),
    )
    rank_order = models.PositiveSmallIntegerField(
        _("Rank progression order"),
        db_index=True,
        help_text=_("Higher numbers indicate higher ranks (e.g., White=1 ... 9th Dan=19)."),
    )
    color_hex = models.CharField(_("Belt badge color"), max_length=7, default="#111827")
    is_black_belt = models.BooleanField(_("Black belt (Dan) level"), default=False)
    is_active = models.BooleanField(_("Active"), default=True)

    class Meta:
        verbose_name = _("Belt type")
        verbose_name_plural = _("Belt types")
        ordering = ["discipline", "rank_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["discipline", "rank_code"],
                name="belt_type_unique_discipline_code",
            ),
            models.UniqueConstraint(
                fields=["discipline", "rank_order"],
                name="belt_type_unique_discipline_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.localized_name} ({self.get_discipline_display()})"

    @property
    def localized_name(self) -> str:
        if normalize_lang() == "ko":
            return self.name_ko or self.name_fa
        return self.name_fa or self.name_ko


class BeltHistoryQuerySet(models.QuerySet):
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


class BeltHistory(ModeratedSubmissionModel):
    """Moderated athlete belt promotion / rank award record."""

    member = models.ForeignKey(
        MemberProfile,
        verbose_name=_("Member"),
        on_delete=models.CASCADE,
        related_name="belt_histories",
    )
    belt_type = models.ForeignKey(
        BeltType,
        verbose_name=_("Belt rank"),
        on_delete=models.PROTECT,
        related_name="belt_histories",
    )
    discipline = models.CharField(
        _("Martial arts discipline"),
        max_length=20,
        choices=Discipline.choices,
        db_index=True,
    )
    award_date = models.DateField(_("Award date"), db_index=True)
    issuing_authority = models.CharField(
        _("Examiner / Federation"),
        max_length=180,
        blank=True,
    )
    notes = models.TextField(_("Additional notes"), blank=True, max_length=1500)
    certificate = models.FileField(
        _("Official belt certificate"),
        storage=private_media_storage,
        upload_to=upload_private_certificate,
        validators=[validate_safe_document],
        blank=True,
    )

    objects = BeltHistoryQuerySet.as_manager()

    class Meta:
        verbose_name = _("Belt history")
        verbose_name_plural = _("Belt histories")
        ordering = ["-award_date", "-belt_type__rank_order", "-id"]
        permissions = [
            ("moderate_belthistory", "Can moderate belt promotion submissions"),
        ]
        indexes = [
            models.Index(
                fields=["member", "approval_status"],
                name="belthist_member_status_idx",
            ),
            models.Index(
                fields=["approval_status", "-award_date"],
                name="belthist_status_date_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.award_date and self.award_date > timezone.localdate():
            raise ValidationError({"award_date": _("Award date cannot be in the future.")})
        if self.belt_type_id:
            if not self.discipline:
                self.discipline = self.belt_type.discipline
            elif self.discipline != self.belt_type.discipline:
                raise ValidationError(
                    {"belt_type": _("Selected belt rank must match the chosen discipline.")}
                )

    def save(self, *args, **kwargs) -> None:
        if self.belt_type_id and not self.discipline:
            self.discipline = self.belt_type.discipline
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.belt_type.localized_name} — {self.award_date}"

    def get_member_url(self) -> str:
        return reverse("belts:member_detail", kwargs={"pk": self.pk})

    def get_certificate_url(self) -> str:
        if not self.certificate:
            return ""
        return reverse("core:protected_file", kwargs={"model_type": "belt", "pk": self.pk})

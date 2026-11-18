"""Medal model supporting Gold, Silver, Bronze, and Other medals with private evidence."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.competitions.models import Competition
from apps.core.models import ApprovalStatus, Discipline, ModeratedSubmissionModel
from apps.core.storage import private_media_storage, upload_private_medal_evidence
from apps.core.translation_utils import normalize_lang
from apps.core.validators import validate_safe_document
from apps.members.models import MemberProfile


class MedalType(models.TextChoices):
    GOLD = "GOLD", _("Gold")
    SILVER = "SILVER", _("Silver")
    BRONZE = "BRONZE", _("Bronze")
    OTHER = "OTHER", _("Other / Special Award")


class MedalQuerySet(models.QuerySet):
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


class Medal(ModeratedSubmissionModel):
    member = models.ForeignKey(
        MemberProfile,
        verbose_name=_("Member"),
        on_delete=models.CASCADE,
        related_name="medals",
    )
    medal_type = models.CharField(
        _("Medal type"),
        max_length=12,
        choices=MedalType.choices,
        db_index=True,
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
        verbose_name=_("Registered competition"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="medals",
    )
    competition_name = models.CharField(
        _("Competition name"),
        max_length=200,
        help_text=_("Competition title (auto-filled when selecting a registered competition)."),
    )
    competition_name_ja = models.CharField(
        _("Competition name (Japanese)"),
        max_length=200,
        blank=True,
    )
    competition_location = models.CharField(_("Competition location"), max_length=200)
    competition_location_ja = models.CharField(
        _("Competition location (Japanese)"),
        max_length=200,
        blank=True,
    )
    division_category = models.CharField(
        _("Division / Category"),
        max_length=140,
        blank=True,
    )
    award_date = models.DateField(_("Award date"), db_index=True)
    evidence = models.FileField(
        _("Supporting evidence / certificate"),
        storage=private_media_storage,
        upload_to=upload_private_medal_evidence,
        validators=[validate_safe_document],
        blank=True,
    )

    objects = MedalQuerySet.as_manager()

    class Meta:
        verbose_name = _("Medal")
        verbose_name_plural = _("Medals")
        ordering = ["-award_date", "-id"]
        permissions = [
            ("moderate_medal", "Can moderate medal submissions"),
        ]
        indexes = [
            models.Index(
                fields=["member", "approval_status", "medal_type"],
                name="medal_member_status_type_idx",
            ),
            models.Index(
                fields=["approval_status", "medal_type", "-award_date"],
                name="medal_public_filter_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.award_date and self.award_date > timezone.localdate():
            raise ValidationError({"award_date": _("Award date cannot be in the future.")})
        if self.competition_id:
            if not self.competition_name:
                self.competition_name = self.competition.title_fa
            if not self.competition_name_ja and self.competition.title_ja:
                self.competition_name_ja = self.competition.title_ja
            if not self.competition_location:
                self.competition_location = self.competition.location_fa
            if not self.competition_location_ja and self.competition.location_ja:
                self.competition_location_ja = self.competition.location_ja

    def save(self, *args, **kwargs) -> None:
        if self.competition_id:
            if not self.competition_name:
                self.competition_name = self.competition.title_fa
            if not self.competition_location:
                self.competition_location = self.competition.location_fa
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.get_medal_type_display()} — {self.localized_competition_name}"

    @property
    def localized_competition_name(self) -> str:
        if self.competition_id:
            return self.competition.localized_title
        if normalize_lang() == "ja":
            return self.competition_name_ja or self.competition_name
        return self.competition_name or self.competition_name_ja

    @property
    def localized_competition_location(self) -> str:
        if self.competition_id:
            return self.competition.localized_location
        if normalize_lang() == "ja":
            return self.competition_location_ja or self.competition_location
        return self.competition_location or self.competition_location_ja

    def get_member_url(self) -> str:
        return reverse("medals:member_detail", kwargs={"pk": self.pk})

    def get_evidence_url(self) -> str:
        if not self.evidence:
            return ""
        return reverse("core:protected_file", kwargs={"model_type": "medal", "pk": self.pk})

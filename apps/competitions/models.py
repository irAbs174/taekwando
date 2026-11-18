"""Competition and moderated CompetitionParticipation models."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
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


class Competition(TimeStampedModel):
    """Official martial arts competition or championship."""

    slug = models.SlugField(_("Slug"), max_length=140, unique=True, db_index=True)
    title_fa = models.CharField(_("Title (Persian)"), max_length=200)
    title_ja = models.CharField(_("Title (Japanese)"), max_length=200, blank=True)
    discipline = models.CharField(
        _("Martial arts discipline"),
        max_length=20,
        choices=Discipline.choices,
        default=Discipline.TAEKWONDO,
        db_index=True,
    )
    location_fa = models.CharField(_("Location (Persian)"), max_length=200)
    location_ja = models.CharField(_("Location (Japanese)"), max_length=200, blank=True)
    start_date = models.DateField(_("Start date"), db_index=True)
    end_date = models.DateField(_("End date"))
    organizer = models.CharField(_("Organizer (Persian)"), max_length=200)
    organizer_ja = models.CharField(_("Organizer (Japanese)"), max_length=200, blank=True)
    description_fa = models.TextField(_("Description (Persian)"), blank=True)
    description_ja = models.TextField(_("Description (Japanese)"), blank=True)
    results_summary_fa = models.TextField(_("Results summary (Persian)"), blank=True)
    results_summary_ja = models.TextField(_("Results summary (Japanese)"), blank=True)
    is_published = models.BooleanField(_("Published"), default=True, db_index=True)

    participants = models.ManyToManyField(
        MemberProfile,
        through="CompetitionParticipation",
        through_fields=("competition", "member"),
        related_name="competitions",
        verbose_name=_("Participants"),
    )

    class Meta:
        verbose_name = _("Competition")
        verbose_name_plural = _("Competitions")
        ordering = ["-start_date", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="competition_end_gte_start",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("End date cannot be earlier than start date.")}
            )

    def __str__(self) -> str:
        return f"{self.localized_title} ({self.start_date.year})"

    @property
    def localized_title(self) -> str:
        return (
            (self.title_ja or self.title_fa)
            if normalize_lang() == "ja"
            else (self.title_fa or self.title_ja)
        )

    @property
    def localized_location(self) -> str:
        return (
            (self.location_ja or self.location_fa)
            if normalize_lang() == "ja"
            else (self.location_fa or self.location_ja)
        )

    @property
    def localized_organizer(self) -> str:
        return (
            (self.organizer_ja or self.organizer)
            if normalize_lang() == "ja"
            else (self.organizer or self.organizer_ja)
        )

    @property
    def localized_description(self) -> str:
        return (
            (self.description_ja or self.description_fa)
            if normalize_lang() == "ja"
            else (self.description_fa or self.description_ja)
        )

    @property
    def localized_results_summary(self) -> str:
        return (
            (self.results_summary_ja or self.results_summary_fa)
            if normalize_lang() == "ja"
            else (self.results_summary_fa or self.results_summary_ja)
        )


class CompetitionParticipationQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(approval_status=ApprovalStatus.APPROVED)

    def publicly_visible(self):
        return self.filter(
            approval_status=ApprovalStatus.APPROVED,
            competition__is_published=True,
            member__user__is_active=True,
            member__membership_status="APPROVED",
            member__public_profile_consent=True,
            member__public_profile_visibility=True,
        )


class CompetitionParticipation(ModeratedSubmissionModel):
    """Member participation and official result in a competition."""

    member = models.ForeignKey(
        MemberProfile,
        verbose_name=_("Member"),
        on_delete=models.CASCADE,
        related_name="competition_participations",
    )
    competition = models.ForeignKey(
        Competition,
        verbose_name=_("Competition"),
        on_delete=models.CASCADE,
        related_name="participations",
    )
    division_category = models.CharField(
        _("Division / Weight category"),
        max_length=140,
        blank=True,
    )
    result = models.CharField(
        _("Result / Standing"),
        max_length=160,
        blank=True,
        help_text=_("Example: 1st Place, Silver Medalist, Quarterfinalist"),
    )
    result_ja = models.CharField(
        _("Result / Standing (Japanese)"),
        max_length=160,
        blank=True,
    )
    placement = models.PositiveSmallIntegerField(
        _("Numeric placement"),
        null=True,
        blank=True,
    )
    notes = models.TextField(_("Notes"), blank=True, max_length=1500)
    certificate = models.FileField(
        _("Participation / result certificate"),
        storage=private_media_storage,
        upload_to=upload_private_certificate,
        validators=[validate_safe_document],
        blank=True,
    )

    objects = CompetitionParticipationQuerySet.as_manager()

    class Meta:
        verbose_name = _("Competition participation")
        verbose_name_plural = _("Competition participations")
        ordering = ["-competition__start_date", "placement", "-id"]
        permissions = [
            (
                "moderate_competitionparticipation",
                "Can moderate competition participation records",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["member", "competition", "division_category"],
                name="comp_participation_unique_member_div",
            ),
        ]
        indexes = [
            models.Index(
                fields=["member", "approval_status"],
                name="comppart_member_status_idx",
            ),
        ]

    def __str__(self) -> str:
        div = f" ({self.division_category})" if self.division_category else ""
        return f"{self.competition.localized_title}{div}"

    @property
    def localized_result(self) -> str:
        if normalize_lang() == "ja":
            return self.result_ja or self.result
        return self.result or self.result_ja

    def get_member_url(self) -> str:
        return reverse("competitions:member_detail", kwargs={"pk": self.pk})

    def get_certificate_url(self) -> str:
        if not self.certificate:
            return ""
        return reverse("core:protected_file", kwargs={"model_type": "competition", "pk": self.pk})

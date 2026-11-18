"""MemberProfile model with strict privacy consent and membership status controls."""
from __future__ import annotations

import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import ApprovalStatus, Discipline, TimeStampedModel
from apps.core.storage import upload_profile_photo
from apps.core.translation_utils import normalize_lang
from apps.core.validators import validate_phone_number, validate_safe_image


class MembershipStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending Review")
    APPROVED = "APPROVED", _("Approved Member")
    REJECTED = "REJECTED", _("Rejected")
    NEEDS_REVISION = "NEEDS_REVISION", _("Needs Revision")
    SUSPENDED = "SUSPENDED", _("Suspended")


class MemberProfileQuerySet(models.QuerySet):
    def approved_members(self):
        return self.filter(
            user__is_active=True,
            membership_status=MembershipStatus.APPROVED,
        )

    def publicly_visible(self):
        """
        Return ONLY active, approved members who explicitly enabled BOTH
        public_profile_consent AND public_profile_visibility.
        """
        return self.filter(
            user__is_active=True,
            membership_status=MembershipStatus.APPROVED,
            public_profile_consent=True,
            public_profile_visibility=True,
        )


class MemberProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User account"),
        on_delete=models.CASCADE,
        related_name="member_profile",
    )
    first_name = models.CharField(_("First name"), max_length=100)
    last_name = models.CharField(_("Last name"), max_length=100)
    first_name_ja = models.CharField(
        _("First name (Japanese)"),
        max_length=100,
        blank=True,
    )
    last_name_ja = models.CharField(
        _("Last name (Japanese)"),
        max_length=100,
        blank=True,
    )
    slug = models.SlugField(_("Public profile slug"), max_length=64, unique=True, db_index=True)
    profile_photo = models.ImageField(
        _("Profile photo"),
        upload_to=upload_profile_photo,
        validators=[validate_safe_image],
        blank=True,
    )
    biography = models.TextField(_("Biography (Persian)"), blank=True, max_length=3000)
    biography_ja = models.TextField(_("Biography (Japanese)"), blank=True, max_length=3000)
    primary_discipline = models.CharField(
        _("Primary discipline"),
        max_length=20,
        choices=Discipline.choices,
        default=Discipline.TAEKWONDO,
        db_index=True,
    )
    # Private fields — NEVER exposed on public champion pages or public APIs
    birth_date = models.DateField(_("Birth date"), null=True, blank=True)
    phone = models.CharField(
        _("Phone number"),
        max_length=25,
        blank=True,
        validators=[validate_phone_number],
    )

    membership_number = models.CharField(
        _("Membership number"),
        max_length=32,
        unique=True,
        db_index=True,
    )
    joining_date = models.DateField(_("Joining date"), default=timezone.localdate)
    membership_status = models.CharField(
        _("Membership status"),
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.PENDING,
        db_index=True,
    )
    admin_note = models.TextField(_("Administrator note"), blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Membership reviewer"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_member_profiles",
    )
    reviewed_at = models.DateTimeField(_("Review date"), null=True, blank=True)

    public_profile_consent = models.BooleanField(
        _("Public profile consent"),
        default=False,
        help_text=_(
            "I consent to displaying my approved sports records and name on the public website."
        ),
    )
    public_profile_visibility = models.BooleanField(
        _("Public profile visibility"),
        default=False,
        help_text=_("Show my athlete profile in the public Champions directory."),
    )

    objects = MemberProfileQuerySet.as_manager()

    class Meta:
        verbose_name = _("Member profile")
        verbose_name_plural = _("Member profiles")
        ordering = ["-joining_date", "-id"]
        permissions = [
            ("approve_membership", "Can approve or reject membership applications"),
        ]
        indexes = [
            models.Index(
                fields=[
                    "membership_status",
                    "public_profile_consent",
                    "public_profile_visibility",
                ],
                name="member_public_vis_idx",
            ),
            models.Index(
                fields=["last_name", "first_name"],
                name="member_name_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.birth_date:
            today = timezone.localdate()
            if self.birth_date > today:
                raise ValidationError({"birth_date": _("Birth date cannot be in the future.")})
            if self.birth_date < today - datetime.timedelta(days=365 * 120):
                raise ValidationError({"birth_date": _("Enter a valid birth date.")})

    def __str__(self) -> str:
        return f"{self.full_name} [{self.membership_number}]"

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.user.get_full_name() or self.user.email

    @property
    def localized_full_name(self) -> str:
        if normalize_lang() == "ja" and (self.last_name_ja or self.first_name_ja):
            # Japanese standard family-name given-name ordering
            return f"{self.last_name_ja} {self.first_name_ja}".strip()
        return self.full_name

    @property
    def localized_biography(self) -> str:
        if normalize_lang() == "ja":
            return self.biography_ja or self.biography
        return self.biography or self.biography_ja

    @property
    def is_publicly_visible(self) -> bool:
        return (
            self.user.is_active
            and self.membership_status == MembershipStatus.APPROVED
            and self.public_profile_consent
            and self.public_profile_visibility
        )

    @property
    def current_approved_belt(self):
        """Return the highest-ranked approved BeltHistory record for this athlete."""
        return (
            self.belt_histories.filter(approval_status=ApprovalStatus.APPROVED)
            .select_related("belt_type")
            .order_by("-belt_type__rank_order", "-award_date", "-id")
            .first()
        )

    def get_public_url(self) -> str:
        return reverse("champions:detail", kwargs={"slug": self.slug})

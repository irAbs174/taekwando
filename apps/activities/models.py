"""SocialActivity model with gated photograph storage and explicit public consent."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import ApprovalStatus, ModeratedSubmissionModel
from apps.core.storage import private_media_storage, upload_private_activity_photo
from apps.core.translation_utils import normalize_lang
from apps.core.validators import validate_safe_image
from apps.members.models import MemberProfile


class SocialActivityQuerySet(models.QuerySet):
    def approved(self):
        return self.filter(approval_status=ApprovalStatus.APPROVED)

    def publicly_visible(self):
        return self.filter(
            approval_status=ApprovalStatus.APPROVED,
            public_visibility_consent=True,
            member__user__is_active=True,
            member__membership_status="APPROVED",
            member__public_profile_consent=True,
            member__public_profile_visibility=True,
        )


class SocialActivity(ModeratedSubmissionModel):
    member = models.ForeignKey(
        MemberProfile,
        verbose_name=_("Member"),
        on_delete=models.CASCADE,
        related_name="social_activities",
    )
    title = models.CharField(_("Activity title"), max_length=200)
    title_ko = models.CharField(_("Activity title (Korean)"), max_length=200, blank=True)

    # Legacy Korean data is retained but not used for Korean.
    title_ja = models.CharField(_("Activity title (Japanese)"), max_length=200, blank=True)
    description = models.TextField(_("Description"), max_length=3000)
    description_ko = models.TextField(
        _("Description (Korean)"),
        blank=True,
        max_length=3000,
    )

    # Legacy Korean data is retained but not used for Korean.
    description_ja = models.TextField(
        _("Description (Japanese)"),
        blank=True,
        max_length=3000,
    )
    activity_date = models.DateField(_("Activity date"), db_index=True)
    location = models.CharField(_("Location"), max_length=200)
    location_ko = models.CharField(_("Location (Korean)"), max_length=200, blank=True)

    # Legacy Korean data is retained but not used for Korean.
    location_ja = models.CharField(_("Location (Japanese)"), max_length=200, blank=True)
    photograph = models.ImageField(
        _("Activity photograph"),
        storage=private_media_storage,
        upload_to=upload_private_activity_photo,
        validators=[validate_safe_image],
        blank=True,
    )
    public_visibility_consent = models.BooleanField(
        _("Public visibility consent"),
        default=False,
        db_index=True,
        help_text=_(
            "Allow displaying this social activity on my public athlete profile once approved."
        ),
    )

    objects = SocialActivityQuerySet.as_manager()

    class Meta:
        verbose_name = _("Social activity")
        verbose_name_plural = _("Social activities")
        ordering = ["-activity_date", "-id"]
        permissions = [
            ("moderate_socialactivity", "Can moderate social activity submissions"),
        ]
        indexes = [
            models.Index(
                fields=["member", "approval_status"],
                name="activity_member_status_idx",
            ),
            models.Index(
                fields=["approval_status", "public_visibility_consent"],
                name="activity_pub_consent_idx",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.activity_date and self.activity_date > timezone.localdate():
            raise ValidationError(
                {"activity_date": _("Activity date cannot be in the future.")}
            )

    def __str__(self) -> str:
        return self.localized_title

    @property
    def administrator_feedback(self) -> str:
        return self.admin_note

    @property
    def localized_title(self) -> str:
        if normalize_lang() == "ko":
            return self.title_ko or self.title
        return self.title or self.title_ko

    @property
    def localized_description(self) -> str:
        if normalize_lang() == "ko":
            return self.description_ko or self.description
        return self.description or self.description_ko

    @property
    def localized_location(self) -> str:
        if normalize_lang() == "ko":
            return self.location_ko or self.location
        return self.location or self.location_ko

    def get_member_url(self) -> str:
        return reverse("activities:member_detail", kwargs={"pk": self.pk})

    def get_photo_url(self) -> str:
        if not self.photograph:
            return ""
        return reverse("core:activity_photo", kwargs={"pk": self.pk})

    def get_private_photo_url(self) -> str:
        if not self.photograph:
            return ""
        return reverse("core:protected_file", kwargs={"model_type": "activity", "pk": self.pk})

"""SEOMetadata and localized SEOTranslation models."""
from __future__ import annotations

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import LanguageChoice, TimeStampedModel
from apps.core.storage import upload_seo_image
from apps.core.translation_utils import resolve_translation
from apps.core.validators import validate_safe_image


class RouteKey(models.TextChoices):
    HOME = "home", _("Homepage")
    ABOUT = "about", _("About Techwando")
    EDUCATION = "education", _("Educational Content")
    SERVICES = "services", _("Training Programs & Services")
    BLOG = "blog", _("Blog Index")
    PRODUCTS = "products", _("Products & Equipment")
    CHAMPIONS = "champions", _("Champions Directory")
    MEDAL_WINNERS = "medal_winners", _("Medal Winners")
    BELT_ACHIEVEMENTS = "belt_achievements", _("Belt Achievements")
    COMPETITION_RESULTS = "competition_results", _("Competition Results")
    CONTACT = "contact", _("Contact Us")


class SEOMetadata(TimeStampedModel):
    """
    Central SEO record bound either to a named public route (`route_key`)
    or generically to a content entity (`content_type` + `object_id`).
    """

    route_key = models.CharField(
        _("Static route key"),
        max_length=40,
        choices=RouteKey.choices,
        unique=True,
        null=True,
        blank=True,
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Linked content model"),
    )
    object_id = models.PositiveBigIntegerField(_("Linked object ID"), null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")

    og_image = models.ImageField(
        _("Open Graph image"),
        upload_to=upload_seo_image,
        validators=[validate_safe_image],
        blank=True,
    )
    robots_index = models.BooleanField(_("Robots index"), default=True)
    robots_follow = models.BooleanField(_("Robots follow"), default=True)

    class Meta:
        verbose_name = _("SEO metadata")
        verbose_name_plural = _("SEO metadata")
        ordering = ["route_key", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "object_id"],
                condition=models.Q(content_type__isnull=False, object_id__isnull=False),
                name="seo_unique_content_object",
            ),
        ]

    def __str__(self) -> str:
        if self.route_key:
            return f"Route: {self.get_route_key_display()}"
        return f"SEO #{self.pk} ({self.content_type} #{self.object_id})"

    def get_translation(self, lang_code: str | None = None):
        return resolve_translation(self, lang_code=lang_code)

    @property
    def robots_directive(self) -> str:
        idx = "index" if self.robots_index else "noindex"
        fol = "follow" if self.robots_follow else "nofollow"
        return f"{idx}, {fol}"


class SEOTranslation(models.Model):
    """Language-specific SEO fields (Persian fa & Japanese ja) for a single SEOMetadata."""

    seo = models.ForeignKey(
        SEOMetadata,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("SEO entry"),
    )
    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LanguageChoice.choices,
    )
    seo_title = models.CharField(_("SEO title"), max_length=160)
    seo_description = models.CharField(_("SEO meta description"), max_length=320, blank=True)
    canonical_url = models.URLField(_("Canonical URL override"), max_length=300, blank=True)
    og_title = models.CharField(_("Open Graph title"), max_length=160, blank=True)
    og_description = models.CharField(
        _("Open Graph description"),
        max_length=320,
        blank=True,
    )
    og_image_alt = models.CharField(_("Open Graph image alt text"), max_length=180, blank=True)

    class Meta:
        verbose_name = _("SEO translation")
        verbose_name_plural = _("SEO translations")
        constraints = [
            models.UniqueConstraint(
                fields=["seo", "language"],
                name="seo_translation_unique_lang",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.language}] {self.seo_title}"

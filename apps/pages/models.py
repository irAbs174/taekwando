"""Page and localized PageTranslation models."""
from __future__ import annotations

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import LanguageChoice, PublicationStatus, TimeStampedModel
from apps.core.storage import upload_blog_image
from apps.core.translation_utils import resolve_translation
from apps.core.validators import validate_safe_image


class PageType(models.TextChoices):
    ABOUT = "ABOUT", _("About Page")
    EDUCATION = "EDUCATION", _("Educational Module")
    SERVICE = "SERVICE", _("Training Program / Service")
    GENERAL = "GENERAL", _("General Static Page")
    LEGAL = "LEGAL", _("Policy / Legal Page")


class PageQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PublicationStatus.PUBLISHED)


class Page(TimeStampedModel):
    slug = models.SlugField(_("Slug"), max_length=140, unique=True, db_index=True)
    page_type = models.CharField(
        _("Page category"),
        max_length=20,
        choices=PageType.choices,
        default=PageType.GENERAL,
        db_index=True,
    )
    status = models.CharField(
        _("Publication status"),
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        db_index=True,
    )
    display_order = models.PositiveSmallIntegerField(_("Display order"), default=0)
    featured_image = models.ImageField(
        _("Featured image"),
        upload_to=upload_blog_image,
        validators=[validate_safe_image],
        blank=True,
    )
    show_in_footer = models.BooleanField(_("Show link in footer"), default=False)
    robots_index = models.BooleanField(_("SEO index"), default=True)
    robots_follow = models.BooleanField(_("SEO follow"), default=True)

    objects = PageQuerySet.as_manager()

    class Meta:
        verbose_name = _("Page")
        verbose_name_plural = _("Pages")
        ordering = ["display_order", "slug"]

    def __str__(self) -> str:
        tr = self.get_translation()
        return tr.title if tr else self.slug

    def get_translation(self, lang_code: str | None = None):
        return resolve_translation(self, lang_code=lang_code)

    def get_absolute_url(self) -> str:
        if self.slug == "about":
            return reverse("pages:about")
        return reverse("pages:detail", kwargs={"slug": self.slug})


class PageTranslation(models.Model):
    page = models.ForeignKey(
        Page,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Page"),
    )
    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LanguageChoice.choices,
    )
    title = models.CharField(_("Title"), max_length=200)
    subtitle = models.CharField(_("Subtitle"), max_length=260, blank=True)
    summary = models.TextField(_("Summary"), blank=True, max_length=600)
    body = models.TextField(_("Page content"))
    featured_image_alt = models.CharField(_("Image alt text"), max_length=180, blank=True)
    seo_title = models.CharField(_("SEO title"), max_length=160, blank=True)
    seo_description = models.CharField(_("SEO description"), max_length=320, blank=True)
    canonical_url = models.URLField(_("Canonical URL"), max_length=300, blank=True)
    og_title = models.CharField(_("Open Graph title"), max_length=160, blank=True)
    og_description = models.CharField(_("Open Graph description"), max_length=320, blank=True)

    class Meta:
        verbose_name = _("Page translation")
        verbose_name_plural = _("Page translations")
        constraints = [
            models.UniqueConstraint(
                fields=["page", "language"],
                name="page_trans_unique_lang",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.language}] {self.title}"

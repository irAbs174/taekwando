"""Blog Category, CategoryTranslation, Tag, Post, and PostTranslation models."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import LanguageChoice, PublicationStatus, TimeStampedModel
from apps.core.storage import upload_blog_image
from apps.core.translation_utils import normalize_lang, resolve_translation
from apps.core.validators import validate_safe_image


class Category(TimeStampedModel):
    slug = models.SlugField(_("Slug"), max_length=100, unique=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(_("Display order"), default=0)
    is_active = models.BooleanField(_("Active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("Blog category")
        verbose_name_plural = _("Blog categories")
        ordering = ["display_order", "slug"]

    def __str__(self) -> str:
        tr = self.get_translation()
        return tr.name if tr else self.slug

    def get_translation(self, lang_code: str | None = None):
        return resolve_translation(self, lang_code=lang_code)

    @property
    def localized_name(self) -> str:
        tr = self.get_translation()
        return tr.name if tr else self.slug


class CategoryTranslation(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Category"),
    )
    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LanguageChoice.choices,
    )
    name = models.CharField(_("Category name"), max_length=120)
    description = models.TextField(_("Description"), blank=True, max_length=600)

    class Meta:
        verbose_name = _("Category translation")
        verbose_name_plural = _("Category translations")
        constraints = [
            models.UniqueConstraint(
                fields=["category", "language"],
                name="blog_category_trans_unique_lang",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.language}] {self.name}"


class Tag(TimeStampedModel):
    slug = models.SlugField(_("Slug"), max_length=80, unique=True, db_index=True)
    name_fa = models.CharField(_("Tag name (Persian)"), max_length=80)
    name_ja = models.CharField(_("Tag name (Japanese)"), max_length=80, blank=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        ordering = ["slug"]

    def __str__(self) -> str:
        return self.localized_name

    @property
    def localized_name(self) -> str:
        if normalize_lang() == "ja":
            return self.name_ja or self.name_fa
        return self.name_fa or self.name_ja


class PostQuerySet(models.QuerySet):
    def published(self):
        """
        Return posts that are PUBLISHED (with published_at null or in the past)
        or SCHEDULED whose scheduled publication timestamp has arrived.
        """
        now = timezone.now()
        return self.filter(
            Q(
                status=PublicationStatus.PUBLISHED,
                published_at__isnull=True,
            )
            | Q(
                status__in=[PublicationStatus.PUBLISHED, PublicationStatus.SCHEDULED],
                published_at__lte=now,
            )
        )


class Post(TimeStampedModel):
    slug = models.SlugField(_("Slug"), max_length=140, unique=True, db_index=True)
    category = models.ForeignKey(
        Category,
        verbose_name=_("Category"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name=_("Tags"),
        blank=True,
        related_name="posts",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.SET_NULL,
        null=True,
        related_name="blog_posts",
    )
    featured_image = models.ImageField(
        _("Featured image"),
        upload_to=upload_blog_image,
        validators=[validate_safe_image],
        blank=True,
    )
    status = models.CharField(
        _("Publication status"),
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        db_index=True,
    )
    published_at = models.DateTimeField(
        _("Publication date"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Set a future date/time with Scheduled status to auto-publish."),
    )
    is_featured = models.BooleanField(_("Featured article"), default=False, db_index=True)
    robots_index = models.BooleanField(_("SEO index"), default=True)
    robots_follow = models.BooleanField(_("SEO follow"), default=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        verbose_name = _("Blog post")
        verbose_name_plural = _("Blog posts")
        ordering = ["-published_at", "-created_at", "-id"]
        indexes = [
            models.Index(
                fields=["status", "-published_at"],
                name="blog_post_status_pub_idx",
            ),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.status == PublicationStatus.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        tr = self.get_translation()
        return tr.title if tr else self.slug

    def get_translation(self, lang_code: str | None = None):
        return resolve_translation(self, lang_code=lang_code)

    def get_absolute_url(self) -> str:
        return reverse("blog:detail", kwargs={"slug": self.slug})


class PostTranslation(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Post"),
    )
    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LanguageChoice.choices,
    )
    title = models.CharField(_("Title"), max_length=220)
    excerpt = models.TextField(_("Excerpt / summary"), blank=True, max_length=600)
    body = models.TextField(_("Article content"))
    featured_image_alt = models.CharField(
        _("Featured image alt text"),
        max_length=180,
        blank=True,
    )
    seo_title = models.CharField(_("SEO title"), max_length=160, blank=True)
    seo_description = models.CharField(_("SEO description"), max_length=320, blank=True)
    canonical_url = models.URLField(_("Canonical URL"), max_length=300, blank=True)
    og_title = models.CharField(_("Open Graph title"), max_length=160, blank=True)
    og_description = models.CharField(_("Open Graph description"), max_length=320, blank=True)

    class Meta:
        verbose_name = _("Post translation")
        verbose_name_plural = _("Post translations")
        constraints = [
            models.UniqueConstraint(
                fields=["post", "language"],
                name="blog_post_trans_unique_lang",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.language}] {self.title}"

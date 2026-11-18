"""ProductCategory, Product, ProductTranslation, and ProductImage models."""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import (
    Discipline,
    LanguageChoice,
    PublicationStatus,
    TimeStampedModel,
)
from apps.core.storage import upload_product_image
from apps.core.translation_utils import normalize_lang, resolve_translation
from apps.core.validators import validate_safe_image


class ProductCategory(TimeStampedModel):
    slug = models.SlugField(_("Slug"), max_length=100, unique=True, db_index=True)
    display_order = models.PositiveSmallIntegerField(_("Display order"), default=0)
    is_active = models.BooleanField(_("Active"), default=True, db_index=True)

    class Meta:
        verbose_name = _("Product category")
        verbose_name_plural = _("Product categories")
        ordering = ["display_order", "slug"]

    def __str__(self) -> str:
        return self.localized_name

    def get_translation(self, lang_code: str | None = None):
        return resolve_translation(self, lang_code=lang_code)

    @property
    def localized_name(self) -> str:
        tr = self.get_translation()
        return tr.name if tr else self.slug


class ProductCategoryTranslation(models.Model):
    category = models.ForeignKey(
        ProductCategory,
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
        verbose_name = _("Product category translation")
        verbose_name_plural = _("Product category translations")
        constraints = [
            models.UniqueConstraint(
                fields=["category", "language"],
                name="product_cat_trans_unique_lang",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.language}] {self.name}"


class ProductQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=PublicationStatus.PUBLISHED)


class Product(TimeStampedModel):
    slug = models.SlugField(_("Slug"), max_length=140, unique=True, db_index=True)
    sku = models.CharField(_("SKU"), max_length=64, unique=True, db_index=True)
    category = models.ForeignKey(
        ProductCategory,
        verbose_name=_("Category"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    discipline = models.CharField(
        _("Recommended discipline"),
        max_length=20,
        choices=Discipline.choices,
        default=Discipline.TAEKWONDO,
        db_index=True,
    )
    price = models.DecimalField(
        _("Price (optional)"),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    currency = models.CharField(_("Currency"), max_length=10, default="JPY", blank=True)
    is_available = models.BooleanField(_("Available for club inquiry"), default=True)
    is_featured = models.BooleanField(_("Featured product"), default=False, db_index=True)
    status = models.CharField(
        _("Publication status"),
        max_length=16,
        choices=PublicationStatus.choices,
        default=PublicationStatus.DRAFT,
        db_index=True,
    )
    robots_index = models.BooleanField(_("SEO index"), default=True)
    robots_follow = models.BooleanField(_("SEO follow"), default=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")
        ordering = ["-is_featured", "-created_at", "-id"]
        indexes = [
            models.Index(fields=["status", "category"], name="product_status_cat_idx"),
        ]

    def __str__(self) -> str:
        tr = self.get_translation()
        name = tr.name if tr else self.slug
        return f"{name} ({self.sku})"

    def get_translation(self, lang_code: str | None = None):
        return resolve_translation(self, lang_code=lang_code)

    @property
    def primary_image(self):
        imgs = list(self.images.all())
        for img in imgs:
            if img.is_primary:
                return img
        return imgs[0] if imgs else None

    def get_absolute_url(self) -> str:
        return reverse("products:detail", kwargs={"slug": self.slug})


class ProductTranslation(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="translations",
        verbose_name=_("Product"),
    )
    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LanguageChoice.choices,
    )
    name = models.CharField(_("Product name"), max_length=200)
    short_description = models.CharField(
        _("Short description"),
        max_length=400,
        blank=True,
    )
    description = models.TextField(_("Detailed description"))
    specifications = models.TextField(
        _("Technical specifications"),
        blank=True,
        help_text=_("One specification per line."),
    )
    seo_title = models.CharField(_("SEO title"), max_length=160, blank=True)
    seo_description = models.CharField(_("SEO description"), max_length=320, blank=True)
    canonical_url = models.URLField(_("Canonical URL"), max_length=300, blank=True)
    og_title = models.CharField(_("Open Graph title"), max_length=160, blank=True)
    og_description = models.CharField(_("Open Graph description"), max_length=320, blank=True)

    class Meta:
        verbose_name = _("Product translation")
        verbose_name_plural = _("Product translations")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "language"],
                name="product_trans_unique_lang",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.language}] {self.name}"


class ProductImage(TimeStampedModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("Product"),
    )
    image = models.ImageField(
        _("Product image"),
        upload_to=upload_product_image,
        validators=[validate_safe_image],
    )
    alt_text_fa = models.CharField(_("Alt text (Persian)"), max_length=180, blank=True)
    alt_text_ja = models.CharField(_("Alt text (Japanese)"), max_length=180, blank=True)
    is_primary = models.BooleanField(_("Primary image"), default=False)
    display_order = models.PositiveSmallIntegerField(_("Display order"), default=0)

    class Meta:
        verbose_name = _("Product image")
        verbose_name_plural = _("Product images")
        ordering = ["-is_primary", "display_order", "id"]

    def __str__(self) -> str:
        return f"Image #{self.pk} for {self.product.sku}"

    @property
    def localized_alt(self) -> str:
        if normalize_lang() == "ja":
            return self.alt_text_ja or self.alt_text_fa or str(self.product)
        return self.alt_text_fa or self.alt_text_ja or str(self.product)

"""Bilingual forms for product catalog and category administration."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.validators import validate_safe_image
from apps.products.models import (
    Product,
    ProductCategory,
    ProductCategoryTranslation,
    ProductImage,
    ProductTranslation,
)


class ProductCategoryBilingualForm(forms.ModelForm):
    fa_name = forms.CharField(
        label=_("Name (Persian)"),
        max_length=120,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_description = forms.CharField(
        label=_("Description (Persian)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "rtl"}),
    )
    ko_name = forms.CharField(
        label=_("Name (Korean)"),
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ko_description = forms.CharField(
        label=_("Description (Korean)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )

    class Meta:
        model = ProductCategory
        fields = ["slug", "display_order", "is_active"]
        widgets = {
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            by_lang = {t.language: t for t in self.instance.translations.all()}
            for code in ("fa", "ko"):
                if code in by_lang:
                    self.fields[f"{code}_name"].initial = by_lang[code].name
                    self.fields[f"{code}_description"].initial = by_lang[code].description

    def save_translations(self, cat: ProductCategory) -> None:
        for code in ("fa", "ko"):
            name = (self.cleaned_data.get(f"{code}_name") or "").strip()
            if name:
                ProductCategoryTranslation.objects.update_or_create(
                    category=cat,
                    language=code,
                    defaults={
                        "name": name,
                        "description": self.cleaned_data.get(f"{code}_description", ""),
                    },
                )


class ProductBilingualForm(forms.ModelForm):
    upload_image = forms.ImageField(
        label=_("Upload Primary Product Image"),
        required=False,
        validators=[validate_safe_image],
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
        ),
    )

    fa_name = forms.CharField(
        label=_("Product Name (Persian)"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_short = forms.CharField(
        label=_("Short Description (Persian)"),
        max_length=400,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_description = forms.CharField(
        label=_("Description (Persian)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5, "dir": "rtl"}),
    )
    fa_specifications = forms.CharField(
        label=_("Specifications (Persian)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "dir": "rtl"}),
    )

    ko_name = forms.CharField(
        label=_("Product Name (Korean)"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ko_short = forms.CharField(
        label=_("Short Description (Korean)"),
        max_length=400,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ko_description = forms.CharField(
        label=_("Description (Korean)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 5, "dir": "ltr"}),
    )
    ko_specifications = forms.CharField(
        label=_("Specifications (Korean)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3, "dir": "ltr"}),
    )

    class Meta:
        model = Product
        fields = [
            "slug",
            "sku",
            "category",
            "discipline",
            "price",
            "currency",
            "is_available",
            "is_featured",
            "status",
            "robots_index",
            "robots_follow",
        ]
        widgets = {
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "sku": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "discipline": forms.Select(attrs={"class": "form-select"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "currency": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "robots_index": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "robots_follow": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            by_lang = {t.language: t for t in self.instance.translations.all()}
            for code in ("fa", "ko"):
                tr = by_lang.get(code)
                if tr:
                    self.fields[f"{code}_name"].initial = tr.name
                    self.fields[f"{code}_short"].initial = tr.short_description
                    self.fields[f"{code}_description"].initial = tr.description
                    self.fields[f"{code}_specifications"].initial = tr.specifications

    def clean(self):
        cleaned = super().clean()
        has_fa = bool(
            (cleaned.get("fa_name") or "").strip() and (cleaned.get("fa_description") or "").strip()
        )
        has_ko = bool(
            (cleaned.get("ko_name") or "").strip() and (cleaned.get("ko_description") or "").strip()
        )
        if not has_fa and not has_ko:
            raise forms.ValidationError(
                _("Provide product name and description in at least one language.")
            )
        return cleaned

    def save_related(self, product: Product) -> None:
        for code in ("fa", "ko"):
            name = (self.cleaned_data.get(f"{code}_name") or "").strip()
            desc = (self.cleaned_data.get(f"{code}_description") or "").strip()
            if name and desc:
                ProductTranslation.objects.update_or_create(
                    product=product,
                    language=code,
                    defaults={
                        "name": name,
                        "short_description": self.cleaned_data.get(f"{code}_short", ""),
                        "description": desc,
                        "specifications": self.cleaned_data.get(f"{code}_specifications", ""),
                    },
                )
        img = self.cleaned_data.get("upload_image")
        if img:
            ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
            ProductImage.objects.create(
                product=product,
                image=img,
                alt_text_fa=self.cleaned_data.get("fa_name", ""),
                alt_text_ko=self.cleaned_data.get("ko_name", ""),
                is_primary=True,
                display_order=0,
            )

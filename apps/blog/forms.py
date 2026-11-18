"""Bilingual editor forms for blog posts and categories."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.blog.models import Category, CategoryTranslation, Post, PostTranslation


class CategoryBilingualForm(forms.ModelForm):
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
    ja_name = forms.CharField(
        label=_("Name (Japanese)"),
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_description = forms.CharField(
        label=_("Description (Japanese)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )

    class Meta:
        model = Category
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
            for code in ("fa", "ja"):
                if code in by_lang:
                    self.fields[f"{code}_name"].initial = by_lang[code].name
                    self.fields[f"{code}_description"].initial = by_lang[code].description

    def save_translations(self, category: Category) -> None:
        for code in ("fa", "ja"):
            name = (self.cleaned_data.get(f"{code}_name") or "").strip()
            if name:
                CategoryTranslation.objects.update_or_create(
                    category=category,
                    language=code,
                    defaults={
                        "name": name,
                        "description": self.cleaned_data.get(f"{code}_description", ""),
                    },
                )


class PostBilingualForm(forms.ModelForm):
    # Persian translation
    fa_title = forms.CharField(
        label=_("Title (Persian)"),
        max_length=220,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_excerpt = forms.CharField(
        label=_("Excerpt (Persian)"),
        max_length=600,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "rtl"}),
    )
    fa_body = forms.CharField(
        label=_("Body (Persian)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 8, "dir": "rtl"}),
    )
    fa_image_alt = forms.CharField(
        label=_("Image Alt (Persian)"),
        max_length=180,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_seo_title = forms.CharField(
        label=_("SEO Title (Persian)"),
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_seo_description = forms.CharField(
        label=_("SEO Description (Persian)"),
        max_length=320,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "rtl"}),
    )

    # Japanese translation
    ja_title = forms.CharField(
        label=_("Title (Japanese)"),
        max_length=220,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_excerpt = forms.CharField(
        label=_("Excerpt (Japanese)"),
        max_length=600,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )
    ja_body = forms.CharField(
        label=_("Body (Japanese)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 8, "dir": "ltr"}),
    )
    ja_image_alt = forms.CharField(
        label=_("Image Alt (Japanese)"),
        max_length=180,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_seo_title = forms.CharField(
        label=_("SEO Title (Japanese)"),
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_seo_description = forms.CharField(
        label=_("SEO Description (Japanese)"),
        max_length=320,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )

    class Meta:
        model = Post
        fields = [
            "slug",
            "category",
            "tags",
            "featured_image",
            "status",
            "published_at",
            "is_featured",
            "robots_index",
            "robots_follow",
        ]
        widgets = {
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "tags": forms.SelectMultiple(attrs={"class": "form-select", "size": 4}),
            "featured_image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "published_at": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "robots_index": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "robots_follow": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            by_lang = {t.language: t for t in self.instance.translations.all()}
            for code in ("fa", "ja"):
                tr = by_lang.get(code)
                if tr:
                    self.fields[f"{code}_title"].initial = tr.title
                    self.fields[f"{code}_excerpt"].initial = tr.excerpt
                    self.fields[f"{code}_body"].initial = tr.body
                    self.fields[f"{code}_image_alt"].initial = tr.featured_image_alt
                    self.fields[f"{code}_seo_title"].initial = tr.seo_title
                    self.fields[f"{code}_seo_description"].initial = tr.seo_description

    def clean(self):
        cleaned = super().clean()
        has_fa = bool((cleaned.get("fa_title") or "").strip() and (cleaned.get("fa_body") or "").strip())
        has_ja = bool((cleaned.get("ja_title") or "").strip() and (cleaned.get("ja_body") or "").strip())
        if not has_fa and not has_ja:
            raise forms.ValidationError(
                _("Provide a complete title and body in at least one language (Persian or Japanese).")
            )
        return cleaned

    def save_translations(self, post: Post) -> None:
        for code in ("fa", "ja"):
            title = (self.cleaned_data.get(f"{code}_title") or "").strip()
            body = (self.cleaned_data.get(f"{code}_body") or "").strip()
            if title and body:
                PostTranslation.objects.update_or_create(
                    post=post,
                    language=code,
                    defaults={
                        "title": title,
                        "excerpt": self.cleaned_data.get(f"{code}_excerpt", ""),
                        "body": body,
                        "featured_image_alt": self.cleaned_data.get(f"{code}_image_alt", ""),
                        "seo_title": self.cleaned_data.get(f"{code}_seo_title", ""),
                        "seo_description": self.cleaned_data.get(f"{code}_seo_description", ""),
                    },
                )

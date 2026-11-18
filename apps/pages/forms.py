"""Bilingual form for managing static, educational, and service pages."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.pages.models import Page, PageTranslation


class PageBilingualForm(forms.ModelForm):
    fa_title = forms.CharField(
        label=_("Title (Persian)"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_subtitle = forms.CharField(
        label=_("Subtitle (Persian)"),
        max_length=260,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_summary = forms.CharField(
        label=_("Summary (Persian)"),
        max_length=600,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "rtl"}),
    )
    fa_body = forms.CharField(
        label=_("Content (Persian)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 7, "dir": "rtl"}),
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

    ja_title = forms.CharField(
        label=_("Title (Japanese)"),
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_subtitle = forms.CharField(
        label=_("Subtitle (Japanese)"),
        max_length=260,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_summary = forms.CharField(
        label=_("Summary (Japanese)"),
        max_length=600,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )
    ja_body = forms.CharField(
        label=_("Content (Japanese)"),
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 7, "dir": "ltr"}),
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
        model = Page
        fields = [
            "slug",
            "page_type",
            "status",
            "display_order",
            "featured_image",
            "show_in_footer",
            "robots_index",
            "robots_follow",
        ]
        widgets = {
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "page_type": forms.Select(attrs={"class": "form-select"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "display_order": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "featured_image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
            "show_in_footer": forms.CheckboxInput(attrs={"class": "form-check-input"}),
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
                    self.fields[f"{code}_subtitle"].initial = tr.subtitle
                    self.fields[f"{code}_summary"].initial = tr.summary
                    self.fields[f"{code}_body"].initial = tr.body
                    self.fields[f"{code}_seo_title"].initial = tr.seo_title
                    self.fields[f"{code}_seo_description"].initial = tr.seo_description

    def clean(self):
        cleaned = super().clean()
        has_fa = bool(
            (cleaned.get("fa_title") or "").strip() and (cleaned.get("fa_body") or "").strip()
        )
        has_ja = bool(
            (cleaned.get("ja_title") or "").strip() and (cleaned.get("ja_body") or "").strip()
        )
        if not has_fa and not has_ja:
            raise forms.ValidationError(
                _("Provide a page title and body in at least one language.")
            )
        return cleaned

    def save_translations(self, page: Page) -> None:
        for code in ("fa", "ja"):
            title = (self.cleaned_data.get(f"{code}_title") or "").strip()
            body = (self.cleaned_data.get(f"{code}_body") or "").strip()
            if title and body:
                PageTranslation.objects.update_or_create(
                    page=page,
                    language=code,
                    defaults={
                        "title": title,
                        "subtitle": self.cleaned_data.get(f"{code}_subtitle", ""),
                        "summary": self.cleaned_data.get(f"{code}_summary", ""),
                        "body": body,
                        "seo_title": self.cleaned_data.get(f"{code}_seo_title", ""),
                        "seo_description": self.cleaned_data.get(f"{code}_seo_description", ""),
                    },
                )

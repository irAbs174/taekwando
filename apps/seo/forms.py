"""Forms for managing route SEO metadata and Persian/Japanese translations."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.seo.models import SEOMetadata


class RouteSEOBilingualForm(forms.ModelForm):
    """Unified bilingual form managing an SEOMetadata record with fa & ja translations."""

    fa_seo_title = forms.CharField(
        label=_("SEO Title (Persian)"),
        max_length=160,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_seo_description = forms.CharField(
        label=_("Meta Description (Persian)"),
        max_length=320,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "rtl"}),
    )
    fa_og_title = forms.CharField(
        label=_("Open Graph Title (Persian)"),
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "rtl"}),
    )
    fa_og_description = forms.CharField(
        label=_("Open Graph Description (Persian)"),
        max_length=320,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "rtl"}),
    )
    fa_canonical_url = forms.URLField(
        label=_("Canonical URL Override (Persian)"),
        required=False,
        widget=forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
    )

    ja_seo_title = forms.CharField(
        label=_("SEO Title (Japanese)"),
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_seo_description = forms.CharField(
        label=_("Meta Description (Japanese)"),
        max_length=320,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )
    ja_og_title = forms.CharField(
        label=_("Open Graph Title (Japanese)"),
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    ja_og_description = forms.CharField(
        label=_("Open Graph Description (Japanese)"),
        max_length=320,
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "dir": "ltr"}),
    )
    ja_canonical_url = forms.URLField(
        label=_("Canonical URL Override (Japanese)"),
        required=False,
        widget=forms.URLInput(attrs={"class": "form-control", "dir": "ltr"}),
    )

    class Meta:
        model = SEOMetadata
        fields = ["route_key", "og_image", "robots_index", "robots_follow"]
        widgets = {
            "route_key": forms.Select(attrs={"class": "form-select"}),
            "og_image": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
            "robots_index": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "robots_follow": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["route_key"].required = True
        if self.instance and self.instance.pk:
            by_lang = {t.language: t for t in self.instance.translations.all()}
            for code in ("fa", "ja"):
                tr = by_lang.get(code)
                if tr:
                    self.fields[f"{code}_seo_title"].initial = tr.seo_title
                    self.fields[f"{code}_seo_description"].initial = tr.seo_description
                    self.fields[f"{code}_og_title"].initial = tr.og_title
                    self.fields[f"{code}_og_description"].initial = tr.og_description
                    self.fields[f"{code}_canonical_url"].initial = tr.canonical_url

    def save_translations(self, seo_obj: SEOMetadata) -> None:
        from apps.seo.models import SEOTranslation

        for code in ("fa", "ja"):
            title = (self.cleaned_data.get(f"{code}_seo_title") or "").strip()
            if title:
                SEOTranslation.objects.update_or_create(
                    seo=seo_obj,
                    language=code,
                    defaults={
                        "seo_title": title,
                        "seo_description": self.cleaned_data.get(f"{code}_seo_description", ""),
                        "og_title": self.cleaned_data.get(f"{code}_og_title", ""),
                        "og_description": self.cleaned_data.get(f"{code}_og_description", ""),
                        "canonical_url": self.cleaned_data.get(f"{code}_canonical_url", ""),
                    },
                )

"""Forms for member belt promotion requests and administrator belt rank configuration."""
from __future__ import annotations

from django import forms

from apps.belts.models import BeltHistory, BeltType


class MemberBeltPromotionForm(forms.ModelForm):
    """Member submission form — strictly excludes approval/reviewer/member fields."""

    class Meta:
        model = BeltHistory
        fields = [
            "belt_type",
            "award_date",
            "issuing_authority",
            "notes",
            "certificate",
        ]
        widgets = {
            "belt_type": forms.Select(attrs={"class": "form-select"}),
            "award_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "issuing_authority": forms.TextInput(attrs={"class": "form-control"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "certificate": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.webp"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["belt_type"].queryset = BeltType.objects.filter(is_active=True).order_by(
            "discipline", "rank_order"
        )

    def clean(self):
        cleaned = super().clean()
        belt_type = cleaned.get("belt_type")
        if belt_type:
            self.instance.discipline = belt_type.discipline
        return cleaned


class BeltTypeAdminForm(forms.ModelForm):
    class Meta:
        model = BeltType
        fields = [
            "discipline",
            "name_fa",
            "name_ko",
            "rank_code",
            "rank_order",
            "color_hex",
            "is_black_belt",
            "is_active",
        ]
        widgets = {
            "discipline": forms.Select(attrs={"class": "form-select"}),
            "name_fa": forms.TextInput(attrs={"class": "form-control"}),
            "name_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "rank_code": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "rank_order": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "color_hex": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
            "is_black_belt": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

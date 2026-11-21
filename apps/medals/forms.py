"""Member medal submission form."""
from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.competitions.models import Competition
from apps.medals.models import Medal


class MemberMedalForm(forms.ModelForm):
    """Strictly excludes member, approval_status, admin_note, reviewer, reviewed_at."""

    class Meta:
        model = Medal
        fields = [
            "medal_type",
            "discipline",
            "competition",
            "competition_name",
            "competition_name_ko",
            "competition_location",
            "competition_location_ko",
            "division_category",
            "award_date",
            "evidence",
        ]
        widgets = {
            "medal_type": forms.Select(attrs={"class": "form-select"}),
            "discipline": forms.Select(attrs={"class": "form-select"}),
            "competition": forms.Select(attrs={"class": "form-select"}),
            "competition_name": forms.TextInput(attrs={"class": "form-control"}),
            "competition_name_ko": forms.TextInput(
                attrs={"class": "form-control", "dir": "ltr"}
            ),
            "competition_location": forms.TextInput(attrs={"class": "form-control"}),
            "competition_location_ko": forms.TextInput(
                attrs={"class": "form-control", "dir": "ltr"}
            ),
            "division_category": forms.TextInput(attrs={"class": "form-control"}),
            "award_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "evidence": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.webp"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["competition"].queryset = Competition.objects.filter(
            is_published=True
        ).order_by("-start_date")
        self.fields["competition_name"].required = False
        self.fields["competition_location"].required = False

    def clean(self):
        cleaned = super().clean()
        comp = cleaned.get("competition")
        if comp:
            if not cleaned.get("competition_name"):
                cleaned["competition_name"] = comp.title_fa
            if not cleaned.get("competition_name_ko"):
                cleaned["competition_name_ko"] = comp.title_ko
            if not cleaned.get("competition_location"):
                cleaned["competition_location"] = comp.location_fa
            if not cleaned.get("competition_location_ko"):
                cleaned["competition_location_ko"] = comp.location_ko
        else:
            if not (cleaned.get("competition_name") or "").strip():
                self.add_error(
                    "competition_name",
                    _("Enter the competition name or select a registered competition."),
                )
            if not (cleaned.get("competition_location") or "").strip():
                self.add_error(
                    "competition_location",
                    _("Enter the competition location."),
                )
        return cleaned

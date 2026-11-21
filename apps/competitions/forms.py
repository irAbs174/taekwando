"""Forms for member competition records and administrator competition management."""
from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.competitions.models import Competition, CompetitionParticipation


class MemberCompetitionParticipationForm(forms.ModelForm):
    class Meta:
        model = CompetitionParticipation
        fields = [
            "competition",
            "division_category",
            "result",
            "result_ko",
            "placement",
            "notes",
            "certificate",
        ]
        widgets = {
            "competition": forms.Select(attrs={"class": "form-select"}),
            "division_category": forms.TextInput(attrs={"class": "form-control"}),
            "result": forms.TextInput(attrs={"class": "form-control"}),
            "result_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "placement": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "certificate": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.webp"}
            ),
        }

    def __init__(self, *args, member=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.member = member
        self.fields["competition"].queryset = Competition.objects.filter(
            is_published=True
        ).order_by("-start_date")

    def clean(self):
        cleaned = super().clean()
        comp = cleaned.get("competition")
        div = (cleaned.get("division_category") or "").strip()
        cleaned["division_category"] = div
        if self.member and comp:
            qs = CompetitionParticipation.objects.filter(
                member=self.member,
                competition=comp,
                division_category=div,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error(
                    "division_category",
                    _("You already submitted a participation record for this competition and division."),
                )
        return cleaned


class CompetitionAdminForm(forms.ModelForm):
    class Meta:
        model = Competition
        fields = [
            "slug",
            "discipline",
            "title_fa",
            "title_ko",
            "location_fa",
            "location_ko",
            "start_date",
            "end_date",
            "organizer",
            "organizer_ko",
            "description_fa",
            "description_ko",
            "results_summary_fa",
            "results_summary_ko",
            "is_published",
        ]
        widgets = {
            "slug": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "discipline": forms.Select(attrs={"class": "form-select"}),
            "title_fa": forms.TextInput(attrs={"class": "form-control"}),
            "title_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "location_fa": forms.TextInput(attrs={"class": "form-control"}),
            "location_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "start_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "organizer": forms.TextInput(attrs={"class": "form-control"}),
            "organizer_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "description_fa": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "description_ko": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "dir": "ltr"}
            ),
            "results_summary_fa": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "results_summary_ko": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "dir": "ltr"}
            ),
            "is_published": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

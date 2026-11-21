"""Member form for submitting and updating sports achievements."""
from __future__ import annotations

from django import forms

from apps.achievements.models import Achievement
from apps.competitions.models import Competition


class MemberAchievementForm(forms.ModelForm):
    """Strictly excludes member, approval_status, admin_note, reviewer, reviewed_at."""

    class Meta:
        model = Achievement
        fields = [
            "title",
            "title_ko",
            "discipline",
            "competition",
            "achievement_date",
            "description",
            "description_ko",
            "certificate",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "title_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "discipline": forms.Select(attrs={"class": "form-select"}),
            "competition": forms.Select(attrs={"class": "form-select"}),
            "achievement_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "description_ko": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "dir": "ltr"}
            ),
            "certificate": forms.FileInput(
                attrs={"class": "form-control", "accept": ".pdf,.jpg,.jpeg,.png,.webp"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["competition"].queryset = Competition.objects.filter(
            is_published=True
        ).order_by("-start_date")

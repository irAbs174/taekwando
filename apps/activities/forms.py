"""Member social activity submission form."""
from django import forms

from apps.activities.models import SocialActivity


class MemberSocialActivityForm(forms.ModelForm):
    """Strictly excludes member, approval_status, admin_note, reviewer, reviewed_at."""

    class Meta:
        model = SocialActivity
        fields = [
            "title",
            "title_ja",
            "activity_date",
            "location",
            "location_ja",
            "description",
            "description_ja",
            "photograph",
            "public_visibility_consent",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "title_ja": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "activity_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "location_ja": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "description_ja": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "dir": "ltr"}
            ),
            "photograph": forms.FileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
            "public_visibility_consent": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

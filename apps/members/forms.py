"""Member profile editing and admin member management forms."""
from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.models import Discipline
from apps.members.models import MemberProfile, MembershipStatus


class MemberProfileEditForm(forms.ModelForm):
    """
    Member-facing profile form. Strictly excludes membership_status,
    membership_number, joining_date, reviewer, reviewed_at, and admin_note.
    """

    class Meta:
        model = MemberProfile
        fields = [
            "first_name",
            "last_name",
            "first_name_ko",
            "last_name_ko",
            "profile_photo",
            "primary_discipline",
            "birth_date",
            "phone",
            "biography",
            "biography_ko",
            "public_profile_consent",
            "public_profile_visibility",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "first_name_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "last_name_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "profile_photo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
            "primary_discipline": forms.Select(attrs={"class": "form-select"}),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "phone": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "biography": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "biography_ko": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "dir": "ltr"}
            ),
            "public_profile_consent": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "public_profile_visibility": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("public_profile_visibility") and not cleaned.get("public_profile_consent"):
            self.add_error(
                "public_profile_consent",
                _("You must grant public profile consent to make your profile visible."),
            )
        return cleaned

    def save(self, commit: bool = True) -> MemberProfile:
        profile = super().save(commit=commit)
        if commit:
            user = profile.user
            if user.first_name != profile.first_name or user.last_name != profile.last_name:
                user.first_name = profile.first_name
                user.last_name = profile.last_name
                user.save(update_fields=["first_name", "last_name", "updated_at"])
        return profile


class AdminMemberProfileForm(forms.ModelForm):
    """Administrator form for editing full member profile attributes."""

    class Meta:
        model = MemberProfile
        fields = [
            "first_name",
            "last_name",
            "first_name_ko",
            "last_name_ko",
            "profile_photo",
            "primary_discipline",
            "birth_date",
            "phone",
            "joining_date",
            "membership_status",
            "admin_note",
            "biography",
            "biography_ko",
            "public_profile_consent",
            "public_profile_visibility",
        ]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "first_name_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "last_name_ko": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "profile_photo": forms.ClearableFileInput(
                attrs={"class": "form-control", "accept": ".jpg,.jpeg,.png,.webp"}
            ),
            "primary_discipline": forms.Select(attrs={"class": "form-select"}),
            "birth_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "phone": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "joining_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"},
                format="%Y-%m-%d",
            ),
            "membership_status": forms.Select(attrs={"class": "form-select"}),
            "admin_note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "biography": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "biography_ko": forms.Textarea(
                attrs={"class": "form-control", "rows": 4, "dir": "ltr"}
            ),
            "public_profile_consent": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "public_profile_visibility": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class MembershipDecisionForm(forms.Form):
    membership_status = forms.ChoiceField(
        label=_("Membership decision"),
        choices=MembershipStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    admin_note = forms.CharField(
        label=_("Administrator note"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )


class ChampionsFilterForm(forms.Form):
    q = forms.CharField(
        label=_("Athlete name"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Search athlete name...")}
        ),
    )
    discipline = forms.ChoiceField(
        label=_("Discipline"),
        required=False,
        choices=[("", _("All disciplines"))] + list(Discipline.choices),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    belt = forms.IntegerField(
        label=_("Belt rank"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    competition = forms.IntegerField(
        label=_("Competition"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    medal_type = forms.ChoiceField(
        label=_("Medal type"),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sort = forms.ChoiceField(
        label=_("Sort by"),
        required=False,
        choices=[
            ("-latest_achievement", _("Newest achievements")),
            ("latest_achievement", _("Oldest achievements")),
            ("-medal_count", _("Most medals")),
            ("name", _("Name (A-Z)")),
        ],
        widget=forms.Select(attrs={"class": "form-select"}),
    )

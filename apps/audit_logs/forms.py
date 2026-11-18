"""Filtering forms for administrative audit log inspection."""
from django import forms
from django.utils.translation import gettext_lazy as _


class AuditLogFilterForm(forms.Form):
    q = forms.CharField(
        label=_("Search"),
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": _("Email, action, model, IP...")}
        ),
    )
    action = forms.CharField(
        label=_("Action"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    target_model = forms.CharField(
        label=_("Target model"),
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

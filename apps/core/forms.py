"""Reusable forms for moderation review and member correction requests."""
from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.models import ApprovalStatus


class ModerationDecisionForm(forms.Form):
    """Server-validated administrator moderation form."""

    DECISION_CHOICES = [
        (ApprovalStatus.APPROVED, _("Approve")),
        (ApprovalStatus.NEEDS_REVISION, _("Request Revision")),
        (ApprovalStatus.REJECTED, _("Reject")),
    ]

    approval_status = forms.ChoiceField(
        label=_("Decision"),
        choices=DECISION_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    admin_note = forms.CharField(
        label=_("Administrator feedback / note"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": _("Provide clear feedback for the athlete..."),
            }
        ),
    )

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("approval_status")
        note = (cleaned.get("admin_note") or "").strip()
        if status in {ApprovalStatus.REJECTED, ApprovalStatus.NEEDS_REVISION} and not note:
            self.add_error(
                "admin_note",
                _("Please provide a reason when rejecting or requesting revision."),
            )
        return cleaned


class CorrectionRequestForm(forms.Form):
    """Allows a member to submit a correction request for a reviewed record."""

    reason = forms.CharField(
        label=_("Correction details"),
        max_length=1500,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": _("Explain what needs to be updated or corrected..."),
            }
        ),
    )

"""Forms for notification actions."""
from django import forms


class NotificationActionForm(forms.Form):
    """Minimal CSRF-validated action form for marking notifications read."""

    redirect_to_target = forms.BooleanField(required=False)

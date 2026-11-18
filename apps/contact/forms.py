"""Public contact form with honeypot anti-spam field and server validation."""
from django import forms
from django.utils.translation import gettext_lazy as _

from apps.contact.models import ContactMessage


class PublicContactForm(forms.ModelForm):
    # Hidden anti-bot honeypot field
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"tabindex": "-1", "autocomplete": "off", "class": "hp-field"}
        ),
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "dir": "ltr"}),
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def clean_message(self) -> str:
        msg = (self.cleaned_data.get("message") or "").strip()
        if len(msg) < 10:
            raise forms.ValidationError(
                _("Please write a message of at least 10 characters.")
            )
        return msg

    def clean_website(self) -> str:
        val = (self.cleaned_data.get("website") or "").strip()
        if val:
            raise forms.ValidationError(_("Spam submission rejected."))
        return val


class ContactAdminNoteForm(forms.Form):
    is_read = forms.BooleanField(
        label=_("Mark as read"),
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    internal_note = forms.CharField(
        label=_("Internal staff note"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

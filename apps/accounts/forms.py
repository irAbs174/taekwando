"""Authentication, registration, password reset, account settings, and admin user forms."""
from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate, password_validation
from django.contrib.auth.forms import (
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
)
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User, UserManager, UserRole
from apps.core.models import Discipline
from apps.core.validators import validate_phone_number


class MemberRegistrationForm(forms.Form):
    """
    Public registration form. Explicitly contains NO role, staff, permission, or
    status fields; AccountService hardcodes role=MEMBER server-side.
    """

    first_name = forms.CharField(
        label=_("First name"),
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}),
    )
    email = forms.EmailField(
        label=_("Email address"),
        max_length=254,
        widget=forms.EmailInput(
            attrs={"class": "form-control", "dir": "ltr", "autocomplete": "email"}
        ),
    )
    phone = forms.CharField(
        label=_("Phone number (optional)"),
        max_length=25,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(
            attrs={"class": "form-control", "dir": "ltr", "autocomplete": "tel"}
        ),
    )
    primary_discipline = forms.ChoiceField(
        label=_("Primary martial arts discipline"),
        choices=Discipline.choices,
        initial=Discipline.TAEKWONDO,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "dir": "ltr", "autocomplete": "new-password"}
        ),
    )
    password2 = forms.CharField(
        label=_("Confirm password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "dir": "ltr", "autocomplete": "new-password"}
        ),
    )
    agree_terms = forms.BooleanField(
        label=_("I agree to the club code of conduct and privacy policy."),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_email(self) -> str:
        email = UserManager.normalize_email(self.cleaned_data.get("email"))
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("An account with this email already exists."))
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", _("The two password fields did not match."))
            else:
                temp_user = User(
                    email=cleaned.get("email", ""),
                    first_name=cleaned.get("first_name", ""),
                    last_name=cleaned.get("last_name", ""),
                )
                try:
                    password_validation.validate_password(p1, user=temp_user)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned


class EmailAuthenticationForm(forms.Form):
    """Email + password login form with explicit inactive-account rejection."""

    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "dir": "ltr",
                "autocomplete": "username",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "dir": "ltr", "autocomplete": "current-password"}
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache: User | None = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        email = UserManager.normalize_email(cleaned.get("email"))
        password = cleaned.get("password")

        if email and password:
            # Check inactive account cleanly after verifying password to avoid leaking existence
            candidate = User.objects.filter(email__iexact=email).first()
            if candidate and not candidate.is_active and candidate.check_password(password):
                raise forms.ValidationError(
                    _("This account is currently deactivated. Please contact the club administrator."),
                    code="inactive",
                )

            self.user_cache = authenticate(self.request, username=email, password=password)
            if self.user_cache is None or not self.user_cache.is_active:
                raise forms.ValidationError(
                    _("Invalid email address or password."),
                    code="invalid_login",
                )
        return cleaned

    def get_user(self) -> User | None:
        return self.user_cache


class AccountSettingsForm(forms.ModelForm):
    """Member account preferences form — never allows changing role or permissions."""

    class Meta:
        model = User
        fields = ["email", "preferred_language"]
        widgets = {
            "email": forms.EmailInput(attrs={"class": "form-control", "dir": "ltr"}),
            "preferred_language": forms.Select(attrs={"class": "form-select"}),
        }

    def clean_email(self) -> str:
        email = UserManager.normalize_email(self.cleaned_data.get("email"))
        qs = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("This email address is already in use."))
        return email


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control", "dir": "ltr"})


class StyledPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].widget.attrs.update({"class": "form-control", "dir": "ltr"})


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control", "dir": "ltr"})


class AdminCreateUserForm(forms.Form):
    """Admin form to create a new member (or staff user when submitted by SUPER_ADMIN)."""

    first_name = forms.CharField(
        label=_("First name"),
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    phone = forms.CharField(
        label=_("Phone number"),
        max_length=25,
        required=False,
        validators=[validate_phone_number],
        widget=forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
    )
    primary_discipline = forms.ChoiceField(
        label=_("Primary discipline"),
        choices=Discipline.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    role = forms.ChoiceField(
        label=_("User role"),
        choices=UserRole.choices,
        initial=UserRole.MEMBER,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    password = forms.CharField(
        label=_("Initial password"),
        strip=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "dir": "ltr", "autocomplete": "new-password"}
        ),
    )
    approve_immediately = forms.BooleanField(
        label=_("Approve membership immediately"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, actor: User | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.actor = actor
        if not (actor and (actor.is_superuser or actor.role == UserRole.SUPER_ADMIN)):
            self.fields["role"].choices = [(UserRole.MEMBER, _("Club Member"))]
            self.fields["role"].initial = UserRole.MEMBER

    def clean_email(self) -> str:
        email = UserManager.normalize_email(self.cleaned_data["email"])
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def clean_password(self) -> str:
        pwd = self.cleaned_data["password"]
        password_validation.validate_password(pwd)
        return pwd

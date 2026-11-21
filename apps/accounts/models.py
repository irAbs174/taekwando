"""Custom email-authenticated User model with server-enforced RBAC roles."""
from __future__ import annotations

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import LanguageChoice


class UserRole(models.TextChoices):
    SUPER_ADMIN = "SUPER_ADMIN", _("Super Administrator")
    CONTENT_ADMIN = "CONTENT_ADMIN", _("Content Administrator")
    CLUB_MANAGER = "CLUB_MANAGER", _("Club Manager")
    MODERATOR = "MODERATOR", _("Moderator")
    MEMBER = "MEMBER", _("Club Member")


STAFF_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.CONTENT_ADMIN,
    UserRole.CLUB_MANAGER,
    UserRole.MODERATOR,
}


class UserManager(BaseUserManager):
    """Manager for email-based User authentication."""

    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str | None) -> str:
        return (email or "").strip().lower()

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError(_("An email address is required."))
        normalized_email = self.normalize_email(email)
        user = self.model(email=normalized_email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        from apps.accounts.rbac import sync_user_role_group

        sync_user_role_group(user)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("role", UserRole.MEMBER)
        role = extra_fields["role"]
        extra_fields.setdefault("is_staff", role in STAFF_ROLES)
        extra_fields.setdefault("is_superuser", role == UserRole.SUPER_ADMIN)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields["role"] = UserRole.SUPER_ADMIN
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["is_active"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom TEAKWONDO user with email login and role-based access control."""

    email = models.EmailField(
        _("Email address"),
        unique=True,
        max_length=254,
        error_messages={"unique": _("A user with this email address already exists.")},
    )
    first_name = models.CharField(_("First name"), max_length=100, blank=True)
    last_name = models.CharField(_("Last name"), max_length=100, blank=True)
    role = models.CharField(
        _("Role"),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.MEMBER,
        db_index=True,
    )
    preferred_language = models.CharField(
        _("Preferred language"),
        max_length=5,
        choices=LanguageChoice.choices,
        default=LanguageChoice.PERSIAN,
    )
    is_active = models.BooleanField(
        _("Active status"),
        default=True,
        db_index=True,
        help_text=_("Designates whether this account can log in."),
    )
    is_staff = models.BooleanField(
        _("Staff status"),
        default=False,
        help_text=_("Designates whether the user can access administration tools."),
    )
    date_joined = models.DateTimeField(_("Date joined"), default=timezone.now)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined", "-id"]
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]
        indexes = [
            models.Index(fields=["role", "is_active"], name="user_role_active_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        self.email = UserManager.normalize_email(self.email)

    def save(self, *args, **kwargs) -> None:
        self.email = UserManager.normalize_email(self.email)
        if self.is_superuser and self.role != UserRole.SUPER_ADMIN:
            self.role = UserRole.SUPER_ADMIN
        if self.role == UserRole.MEMBER:
            self.is_staff = False
            self.is_superuser = False
        elif self.role == UserRole.SUPER_ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role in STAFF_ROLES:
            self.is_staff = True
            self.is_superuser = False
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        full = self.get_full_name()
        return f"{full} ({self.email})" if full else self.email

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self) -> str:
        return self.first_name or self.email.split("@")[0]

    @property
    def is_admin_role(self) -> bool:
        return self.is_superuser or self.role in STAFF_ROLES

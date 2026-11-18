"""ContactMessage model storing public inquiries with read status and language."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import LanguageChoice


class ContactMessage(models.Model):
    name = models.CharField(_("Full name"), max_length=120)
    email = models.EmailField(_("Email address"), max_length=254)
    subject = models.CharField(_("Subject"), max_length=200)
    message = models.TextField(_("Message"), max_length=4000)
    language = models.CharField(
        _("Language"),
        max_length=5,
        choices=LanguageChoice.choices,
        default=LanguageChoice.PERSIAN,
        db_index=True,
    )
    is_read = models.BooleanField(_("Read status"), default=False, db_index=True)
    read_at = models.DateTimeField(_("Read at"), null=True, blank=True)
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Reviewed by"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_contact_messages",
    )
    internal_note = models.TextField(_("Internal staff note"), blank=True, max_length=2000)
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
        unpack_ipv4=True,
    )
    submitted_at = models.DateTimeField(_("Submission date"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Contact message")
        verbose_name_plural = _("Contact messages")
        ordering = ["-submitted_at", "-id"]

    def __str__(self) -> str:
        return f"{self.subject} — {self.name} <{self.email}>"

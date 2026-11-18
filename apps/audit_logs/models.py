"""Immutable audit trail recording actor, action, target, before/after state, and IP."""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AuditLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Actor"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    actor_email = models.CharField(
        _("Actor email snapshot"),
        max_length=255,
        blank=True,
    )
    action = models.CharField(_("Action"), max_length=80, db_index=True)
    target_model = models.CharField(_("Target model"), max_length=120, db_index=True)
    target_id = models.CharField(_("Target ID"), max_length=64, blank=True, db_index=True)
    target_repr = models.CharField(_("Target summary"), max_length=255, blank=True)
    previous_state = models.JSONField(_("Previous state"), default=dict, blank=True)
    new_state = models.JSONField(_("New state"), default=dict, blank=True)
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
        unpack_ipv4=True,
    )
    user_agent = models.CharField(_("User agent"), max_length=300, blank=True)
    created_at = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _("Audit log")
        verbose_name_plural = _("Audit logs")
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["target_model", "target_id"], name="audit_target_idx"),
            models.Index(fields=["action", "-created_at"], name="audit_action_time_idx"),
        ]

    def __str__(self) -> str:
        who = self.actor_email or "system"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {who} {self.action} {self.target_model}#{self.target_id}"

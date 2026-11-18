from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AuditLogsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit_logs"
    verbose_name = _("Audit Logs")

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class BeltsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.belts"
    verbose_name = _("Belts & Rankings")

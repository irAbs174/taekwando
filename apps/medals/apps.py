from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MedalsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.medals"
    verbose_name = _("Medals")

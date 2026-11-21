from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _


def _sync_roles_after_migrate(sender, **kwargs) -> None:
    from apps.accounts.rbac import ensure_role_groups

    ensure_role_groups()


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = _("Accounts & Roles")

    def ready(self) -> None:
        post_migrate.connect(
            _sync_roles_after_migrate,
            dispatch_uid="teakwondo_ensure_role_groups",
        )

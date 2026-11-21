from django.apps import AppConfig
from django.db.backends.signals import connection_created


def _configure_sqlite_connection(sender, connection, **kwargs) -> None:
    """Apply safe, portable SQLite pragmas without affecting PostgreSQL."""
    if connection.vendor != "sqlite":
        return
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA foreign_keys = ON;")
        cursor.execute("PRAGMA busy_timeout = 5000;")
        db_name = str(connection.settings_dict.get("NAME", ""))
        if db_name and db_name != ":memory:" and "mode=memory" not in db_name:
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Core & Moderation"

    def ready(self) -> None:
        connection_created.connect(
            _configure_sqlite_connection,
            dispatch_uid="teakwondo_sqlite_pragmas",
        )

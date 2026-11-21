"""Development settings for TEAKWONDO."""
import os

from .base import *  # noqa: F401,F403
from .base import env_bool, env_list

# Local-only fallback key; production.py requires DJANGO_SECRET_KEY from environment.
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-teakwondo-dev-only-key-do-not-use-in-production-9f4c2a1b8e",
)

DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0", ".e2b.app", "testserver"],
)

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://*.e2b.app",
    ],
)

# Use standard staticfiles storage in dev so `collectstatic` isn't required on every edit
STORAGES = {
    **STORAGES,
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Optional dev preview iframe support when running inside sandboxed browser previews.
# Production and testing strictly enforce X_FRAME_OPTIONS = "DENY".
if env_bool("DEV_ALLOW_PREVIEW_IFRAME", False):
    MIDDLEWARE = [
        m for m in MIDDLEWARE if m != "django.middleware.clickjacking.XFrameOptionsMiddleware"
    ]
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True
    LANGUAGE_COOKIE_SAMESITE = "None"
    LANGUAGE_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

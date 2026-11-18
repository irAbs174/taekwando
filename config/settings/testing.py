"""Testing settings for TECHWANDO automated test suite."""
import tempfile
from pathlib import Path

from .base import *  # noqa: F401,F403

SECRET_KEY = "test-only-secret-key-for-techwando-automated-suite-9876543210abcdef"
DEBUG = False

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
CSRF_TRUSTED_ORIGINS = ["http://testserver", "http://localhost"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hashing during test runs (Argon2 is still verified in dedicated test)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

_TEST_TMP = Path(tempfile.mkdtemp(prefix="techwando_test_media_"))
MEDIA_ROOT = _TEST_TMP / "media"
PRIVATE_MEDIA_ROOT = _TEST_TMP / "private_media"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
PRIVATE_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Relax generic API throttling in unit tests (login/contact rate-limit tests test explicitly)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10000/minute",
        "user": "10000/minute",
        "contact": "5/hour",
    },
}

LOGGING["handlers"]["file"] = {"class": "logging.NullHandler"}
LOGGING["handlers"]["security_file"] = {"class": "logging.NullHandler"}
LOGGING["handlers"]["console"] = {"class": "logging.NullHandler"}

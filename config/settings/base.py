"""
Base Django settings for TECHWANDO.
Shared across development, testing, and production environments.
"""
from __future__ import annotations

import os
from pathlib import Path
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_dotenv(dotenv_path: Path) -> None:
    """Minimal, zero-dependency .env parser that respects existing OS env vars."""
    if not dotenv_path.is_file():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int = 0) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw.strip())


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return list(default or [])
    return [item.strip() for item in raw.split(",") if item.strip()]


# -----------------------------------------------------------------------------
# Site Metadata
# -----------------------------------------------------------------------------
SITE_NAME = os.environ.get("SITE_NAME", "TECHWANDO")
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "http://localhost:8000").rstrip("/")
DJANGO_ADMIN_URL = os.environ.get("DJANGO_ADMIN_URL", "django-admin/").lstrip("/")
if not DJANGO_ADMIN_URL.endswith("/"):
    DJANGO_ADMIN_URL += "/"
CLUB_CONTACT_EMAIL = os.environ.get("CLUB_CONTACT_EMAIL", "info@techwando.example.com")
CLUB_PHONE = os.environ.get("CLUB_PHONE", "+98 21 8888 0000")
CLUB_ADDRESS = {
    "fa": os.environ.get(
        "CLUB_ADDRESS_FA",
        "تهران، خیابان ولیعصر، بالاتر از پارک ساعی، پلاک ۱۲۴، طبقه دوم",
    ),
    "ko": os.environ.get(
        "CLUB_ADDRESS_KO",
        "테헤란 발리아스르 거리 124번지 2층 (사이 공원 북쪽)",
    ),
}
CLUB_TRAINING_HOURS = {
    "fa": os.environ.get("CLUB_HOURS_FA", "شنبه تا پنجشنبه، ۹:۰۰ تا ۲۱:۰۰"),
    "ko": os.environ.get("CLUB_HOURS_KO", "토요일~목요일 9:00~21:00"),
}
CLUB_SOCIAL_LINKS = [
    {
        "label": "Instagram",
        "icon": "bi-instagram",
        "url": os.environ.get("CLUB_INSTAGRAM_URL", "https://www.instagram.com/techwando"),
    },
    {
        "label": "YouTube",
        "icon": "bi-youtube",
        "url": os.environ.get("CLUB_YOUTUBE_URL", "https://www.youtube.com/@techwando"),
    },
    {
        "label": "Telegram",
        "icon": "bi-telegram",
        "url": os.environ.get("CLUB_TELEGRAM_URL", "https://t.me/techwando"),
    },
]

# Featured coaching team shown on the homepage and About page.
# Configuration-driven so the frontend needs no database schema change.
# Names are content (not interface strings); roles are translated via gettext.
CLUB_INSTRUCTORS = [
    {
        "name_fa": "استاد رضا موسوی",
        "name_ko": "레자 무사비 사범",
        "role": _("Technical Director & Head Coach"),
        "discipline": _("Taekwondo"),
        "rank_fa": "دان ۴ — استاد",
        "rank_ko": "4단 사범",
        "photo": "images/placeholders/instructor-1.svg",
    },
    {
        "name_fa": "استاد هاروکی تاناکا",
        "name_ko": "다나카 하루키 사범",
        "role": _("Karate & Kata Program Lead"),
        "discipline": _("Karate"),
        "rank_fa": "دان ۳ کاراته",
        "rank_ko": "가라테 3단",
        "photo": "images/placeholders/instructor-2.svg",
    },
    {
        "name_fa": "استاد سارا احمدی",
        "name_ko": "사라 아흐마디 사범",
        "role": _("Youth Development & Conditioning"),
        "discipline": _("Judo"),
        "rank_fa": "دان ۲ جودو",
        "rank_ko": "유도 2단",
        "photo": "images/placeholders/instructor-3.svg",
    },
]

# -----------------------------------------------------------------------------
# Application Definition
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "django_filters",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.members",
    "apps.belts",
    "apps.competitions",
    "apps.achievements",
    "apps.medals",
    "apps.activities",
    "apps.blog",
    "apps.products",
    "apps.contact",
    "apps.pages",
    "apps.seo",
    "apps.notifications",
    "apps.audit_logs",
    "apps.api",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.middleware.ActiveUserAndSecurityHeadersMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_context",
            ],
        },
    },
]

# -----------------------------------------------------------------------------
# Database (SQLite default; seamless PostgreSQL migration via environment vars)
# -----------------------------------------------------------------------------
DB_ENGINE = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")

if DB_ENGINE == "django.db.backends.sqlite3":
    _db_name = os.environ.get("DB_NAME", "db.sqlite3")
    _db_path = Path(_db_name) if Path(_db_name).is_absolute() else BASE_DIR / _db_name
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _db_path,
            "OPTIONS": {
                "timeout": 20,
            },
            "ATOMIC_REQUESTS": False,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": os.environ.get("DB_NAME", "techwando"),
            "USER": os.environ.get("DB_USER", "techwando"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "5432"),
            "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
            "CONN_HEALTH_CHECKS": True,
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Cache (used for rate limiting & throttling)
# -----------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "techwando-default-cache",
    }
}

# -----------------------------------------------------------------------------
# Authentication, Password Security & Sessions
# -----------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:post_login_redirect"
LOGOUT_REDIRECT_URL = "pages:home"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {"user_attributes": ("email", "first_name", "last_name")},
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 12  # 12 hours
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

CSRF_COOKIE_HTTPONLY = False  # Enables same-origin DRF/fetch X-CSRFToken header
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_USE_SESSIONS = False

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", False)

# Login and contact rate limiting
LOGIN_RATE_LIMIT_ATTEMPTS = env_int("LOGIN_RATE_LIMIT_ATTEMPTS", 5)
LOGIN_RATE_LIMIT_WINDOW = env_int("LOGIN_RATE_LIMIT_WINDOW", 300)
CONTACT_RATE_LIMIT_ATTEMPTS = env_int("CONTACT_RATE_LIMIT_ATTEMPTS", 5)
CONTACT_RATE_LIMIT_WINDOW = env_int("CONTACT_RATE_LIMIT_WINDOW", 600)

# -----------------------------------------------------------------------------
# Internationalization & Localization (Persian fa-IR RTL & Korean ko-KR LTR)
# -----------------------------------------------------------------------------
LANGUAGE_CODE = os.environ.get("DJANGO_DEFAULT_LANGUAGE", "fa")
if LANGUAGE_CODE not in {"fa", "ko"}:
    LANGUAGE_CODE = "fa"

LANGUAGES = [
    ("fa", _("Persian")),
    ("ko", _("Korean")),
]

LANGUAGE_LOCALES = {
    "fa": {"bcp47": "fa-IR", "og_locale": "fa_IR", "dir": "rtl", "native": "فارسی"},
    "ko": {"bcp47": "ko-KR", "og_locale": "ko_KR", "dir": "ltr", "native": "한국어"},
}

LANGUAGE_COOKIE_NAME = "techwando_lang"
LANGUAGE_COOKIE_AGE = 60 * 60 * 24 * 365
LANGUAGE_COOKIE_SAMESITE = "Lax"
LANGUAGE_COOKIE_HTTPONLY = True

LOCALE_PATHS = [BASE_DIR / "locale"]

TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static & Media Files (with isolated Private Media Storage)
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Sensitive uploads (certificates, medal evidence, private activity photos)
# live OUTSIDE MEDIA_ROOT and are NEVER served directly by static/media routes.
PRIVATE_MEDIA_ROOT = BASE_DIR / "private_media"
USE_X_ACCEL_REDIRECT = env_bool("USE_X_ACCEL_REDIRECT", False)
X_ACCEL_REDIRECT_PREFIX = os.environ.get("X_ACCEL_REDIRECT_PREFIX", "/_private_media")

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MAX_UPLOAD_SIZE_MB = env_int("MAX_UPLOAD_SIZE_MB", 5)
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES
DATA_UPLOAD_MAX_MEMORY_SIZE = (MAX_UPLOAD_SIZE_MB + 3) * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}

# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "TECHWANDO <noreply@techwando.example.com>"
)

# -----------------------------------------------------------------------------
# Django REST Framework & OpenAPI (drf-spectacular)
# -----------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.api.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.api.exceptions.consistent_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/minute",
        "user": "300/minute",
        "contact": "5/hour",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

SPECTACULAR_SETTINGS = {
    "TITLE": "TECHWANDO Platform API",
    "DESCRIPTION": (
        "Multilingual (Persian fa-IR & Korean ko-KR) Martial Arts, Sports Education, "
        "Club Management, Athlete Profiles, Achievements, and Medal Management REST API."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "DisciplineEnum": "apps.core.models.Discipline.choices",
        "ApprovalStatusEnum": "apps.core.models.ApprovalStatus.choices",
        "MembershipStatusEnum": "apps.members.models.MembershipStatus.choices",
        "PublicationStatusEnum": "apps.core.models.PublicationStatus.choices",
    },
}

# -----------------------------------------------------------------------------
# Pagination
# -----------------------------------------------------------------------------
PUBLIC_PAGE_SIZE = 12
DASHBOARD_PAGE_SIZE = 10

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DJANGO_LOG_LEVEL = os.environ.get("DJANGO_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "techwando.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "standard",
            "encoding": "utf-8",
        },
        "security_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_DIR / "security.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 10,
            "formatter": "standard",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "file"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "django.security": {
            "handlers": ["console", "security_file"],
            "level": "WARNING",
            "propagate": False,
        },
        "techwando": {
            "handlers": ["console", "file"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },
        "techwando.security": {
            "handlers": ["console", "security_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

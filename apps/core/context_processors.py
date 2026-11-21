"""Global template context processor for multilingual layout, SEO, and counters."""
from __future__ import annotations

from django.conf import settings
from django.utils import timezone
from django.urls import translate_url

from apps.core.permissions import can_access_admin_portal, can_manage_content, can_manage_members
from apps.core.translation_utils import normalize_lang


def site_context(request) -> dict:
    current_lang = normalize_lang(getattr(request, "LANGUAGE_CODE", None))
    alt_lang = "ko" if current_lang == "fa" else "fa"
    locale_meta = settings.LANGUAGE_LOCALES.get(current_lang, settings.LANGUAGE_LOCALES["fa"])
    alt_locale_meta = settings.LANGUAGE_LOCALES.get(alt_lang, settings.LANGUAGE_LOCALES["ko"])

    full_path = request.get_full_path()
    fa_path = translate_url(full_path, "fa")
    ko_path = translate_url(full_path, "ko")
    if not fa_path.startswith("/fa/"):
        fa_path = "/fa/"
    if not ko_path.startswith("/ko/"):
        ko_path = "/ko/"

    # Canonical path without query string for hreflang links
    clean_path = request.path
    fa_clean = translate_url(clean_path, "fa")
    ko_clean = translate_url(clean_path, "ko")
    base_url = settings.SITE_BASE_URL

    unread_notifications = 0
    is_admin_portal_user = False
    is_club_manager = False
    is_content_admin = False

    user = getattr(request, "user", None)
    if user and user.is_authenticated and user.is_active:
        unread_notifications = user.notifications.filter(is_read=False).count()
        is_admin_portal_user = can_access_admin_portal(user)
        is_club_manager = can_manage_members(user)
        is_content_admin = can_manage_content(user)

    instructors = [
        {
            "name": person.get(f"name_{current_lang}") or person.get("name_fa", ""),
            "role": person.get("role", ""),
            "discipline": person.get("discipline", ""),
            "rank": person.get(f"rank_{current_lang}") or person.get("rank_fa", ""),
            "photo": person.get("photo", ""),
        }
        for person in getattr(settings, "CLUB_INSTRUCTORS", [])
    ]

    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_BASE_URL": base_url,
        "CLUB_CONTACT_EMAIL": settings.CLUB_CONTACT_EMAIL,
        "CLUB_PHONE": getattr(settings, "CLUB_PHONE", ""),
        "CLUB_ADDRESS": getattr(settings, "CLUB_ADDRESS", {}).get(current_lang, ""),
        "CLUB_TRAINING_HOURS": getattr(settings, "CLUB_TRAINING_HOURS", {}).get(
            current_lang, ""
        ),
        "CLUB_SOCIAL_LINKS": getattr(settings, "CLUB_SOCIAL_LINKS", []),
        "CLUB_INSTRUCTORS": instructors,
        "CURRENT_YEAR": timezone.localdate().year,
        "CURRENT_LANG": current_lang,
        "ALT_LANG": alt_lang,
        "IS_RTL": locale_meta["dir"] == "rtl",
        "HTML_DIR": locale_meta["dir"],
        "LOCALE_META": locale_meta,
        "ALT_LOCALE_META": alt_locale_meta,
        "SWITCH_URL_FA": fa_path,
        "SWITCH_URL_KO": ko_path,
        "HREFLANG_FA": f"{base_url}{fa_clean}",
        "HREFLANG_KO": f"{base_url}{ko_clean}",
        "CANONICAL_DEFAULT": f"{base_url}{clean_path}",
        "UNREAD_NOTIFICATIONS_COUNT": unread_notifications,
        "IS_ADMIN_PORTAL_USER": is_admin_portal_user,
        "IS_CLUB_MANAGER": is_club_manager,
        "IS_CONTENT_ADMIN": is_content_admin,
    }

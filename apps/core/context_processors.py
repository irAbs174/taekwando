"""Global template context processor for multilingual layout, SEO, and counters."""
from __future__ import annotations

from django.conf import settings
from django.urls import translate_url

from apps.core.permissions import can_access_admin_portal, can_manage_content, can_manage_members
from apps.core.translation_utils import normalize_lang


def site_context(request) -> dict:
    current_lang = normalize_lang(getattr(request, "LANGUAGE_CODE", None))
    alt_lang = "ja" if current_lang == "fa" else "fa"
    locale_meta = settings.LANGUAGE_LOCALES.get(current_lang, settings.LANGUAGE_LOCALES["fa"])
    alt_locale_meta = settings.LANGUAGE_LOCALES.get(alt_lang, settings.LANGUAGE_LOCALES["ja"])

    full_path = request.get_full_path()
    fa_path = translate_url(full_path, "fa")
    ja_path = translate_url(full_path, "ja")
    if not fa_path.startswith("/fa/"):
        fa_path = "/fa/"
    if not ja_path.startswith("/ja/"):
        ja_path = "/ja/"

    # Canonical path without query string for hreflang links
    clean_path = request.path
    fa_clean = translate_url(clean_path, "fa")
    ja_clean = translate_url(clean_path, "ja")
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

    return {
        "SITE_NAME": settings.SITE_NAME,
        "SITE_BASE_URL": base_url,
        "CLUB_CONTACT_EMAIL": settings.CLUB_CONTACT_EMAIL,
        "CURRENT_LANG": current_lang,
        "ALT_LANG": alt_lang,
        "IS_RTL": locale_meta["dir"] == "rtl",
        "HTML_DIR": locale_meta["dir"],
        "LOCALE_META": locale_meta,
        "ALT_LOCALE_META": alt_locale_meta,
        "SWITCH_URL_FA": fa_path,
        "SWITCH_URL_JA": ja_path,
        "HREFLANG_FA": f"{base_url}{fa_clean}",
        "HREFLANG_JA": f"{base_url}{ja_clean}",
        "CANONICAL_DEFAULT": f"{base_url}{clean_path}",
        "UNREAD_NOTIFICATIONS_COUNT": unread_notifications,
        "IS_ADMIN_PORTAL_USER": is_admin_portal_user,
        "IS_CLUB_MANAGER": is_club_manager,
        "IS_CONTENT_ADMIN": is_content_admin,
    }

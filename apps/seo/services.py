"""Helpers for building page SEO context, Open Graph tags, and JSON-LD structured data."""
from __future__ import annotations

import json

from django.conf import settings
from django.templatetags.static import static

from apps.core.translation_utils import normalize_lang
from apps.seo.models import SEOMetadata


def build_seo_context(
    request,
    *,
    route_key: str | None = None,
    default_title: str = "",
    default_description: str = "",
    canonical_url: str = "",
    og_title: str = "",
    og_description: str = "",
    og_image_url: str = "",
    og_image_alt: str = "",
    og_type: str = "website",
    robots_index: bool = True,
    robots_follow: bool = True,
    structured_data: dict | list | None = None,
) -> dict:
    """Resolve localized SEO tags merging route overrides, object fields, and defaults."""
    lang = normalize_lang(getattr(request, "LANGUAGE_CODE", None))
    base_url = settings.SITE_BASE_URL

    if route_key:
        seo_obj = (
            SEOMetadata.objects.prefetch_related("translations")
            .filter(route_key=route_key)
            .first()
        )
        if seo_obj:
            robots_index = seo_obj.robots_index
            robots_follow = seo_obj.robots_follow
            if seo_obj.og_image and not og_image_url:
                og_image_url = f"{base_url}{seo_obj.og_image.url}"
            tr = seo_obj.get_translation(lang)
            if tr:
                default_title = tr.seo_title or default_title
                default_description = tr.seo_description or default_description
                canonical_url = tr.canonical_url or canonical_url
                og_title = tr.og_title or tr.seo_title or og_title
                og_description = tr.og_description or tr.seo_description or og_description
                og_image_alt = tr.og_image_alt or og_image_alt

    title = default_title or settings.SITE_NAME
    if settings.SITE_NAME.lower() not in title.lower():
        full_title = f"{title} | {settings.SITE_NAME}"
    else:
        full_title = title

    if not default_description:
        default_description = (
            "پلتفرم جامع آموزش هنرهای رزمی، مدیریت باشگاه تکواندو، پروفایل قهرمانان و افتخارات ورزشی."
            if lang == "fa"
            else "TEAKWONDO — 무술 교육, 클럽 운영, 공인 선수 프로필 및 메달 기록 관리 플랫폼."
        )

    final_canonical = canonical_url or f"{base_url}{request.path}"
    final_og_image = og_image_url or f"{base_url}{static('images/og-default.svg')}"
    if final_og_image.startswith("/"):
        final_og_image = f"{base_url}{final_og_image}"

    robots = f"{'index' if robots_index else 'noindex'}, {'follow' if robots_follow else 'nofollow'}"

    if structured_data is None:
        structured_data = {
            "@context": "https://schema.org",
            "@type": "SportsClub",
            "name": settings.SITE_NAME,
            "url": f"{base_url}/{lang}/",
            "inLanguage": settings.LANGUAGE_LOCALES[lang]["bcp47"],
            "description": default_description,
            "sport": ["Taekwondo", "Karate", "Judo", "Martial Arts"],
            "email": settings.CLUB_CONTACT_EMAIL,
        }

    return {
        "seo_title": full_title,
        "seo_description": default_description,
        "seo_canonical": final_canonical,
        "og_title": og_title or full_title,
        "og_description": og_description or default_description,
        "og_image": final_og_image,
        "og_image_alt": og_image_alt or settings.SITE_NAME,
        "og_type": og_type,
        "seo_robots": robots,
        "structured_data_json": json.dumps(structured_data, ensure_ascii=False),
    }

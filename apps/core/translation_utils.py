"""Multilingual database content translation lookup with automatic fallback."""
from __future__ import annotations

from django.conf import settings
from django.utils import translation

SUPPORTED_LANGUAGES = ("fa", "ja")


def normalize_lang(lang_code: str | None = None) -> str:
    code = (lang_code or translation.get_language() or settings.LANGUAGE_CODE or "fa").lower()
    base = code.split("-")[0]
    return base if base in SUPPORTED_LANGUAGES else settings.LANGUAGE_CODE


def get_fallback_lang(lang_code: str) -> str:
    norm = normalize_lang(lang_code)
    return "ja" if norm == "fa" else "fa"


def resolve_translation(obj, lang_code: str | None = None, relation_name: str = "translations"):
    """
    Resolve the translation record for `obj` in `lang_code` (defaulting to the
    active language), falling back cleanly to the alternate supported language.
    Uses prefetched relation cache when available to avoid N+1 queries.
    Attaches `is_fallback = True` when returning a fallback translation.
    """
    if obj is None:
        return None
    target = normalize_lang(lang_code)
    fallback = get_fallback_lang(target)
    manager = getattr(obj, relation_name, None)
    if manager is None:
        return None

    items = list(manager.all())
    by_lang = {item.language: item for item in items}

    if target in by_lang:
        chosen = by_lang[target]
        chosen.is_fallback = False
        return chosen
    if fallback in by_lang:
        chosen = by_lang[fallback]
        chosen.is_fallback = True
        return chosen
    if items:
        chosen = items[0]
        chosen.is_fallback = True
        return chosen
    return None

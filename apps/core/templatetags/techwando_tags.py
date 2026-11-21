"""Template tags and filters for Persian/Korean typography, dates, and URLs."""
from __future__ import annotations

import datetime

from django import template
from django.urls import translate_url
from django.utils import timezone

from apps.core.translation_utils import normalize_lang, resolve_translation

register = template.Library()

_PERSIAN_DIGIT_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

_PERSIAN_MONTHS = {
    1: "ژانویه",
    2: "فوریه",
    3: "مارس",
    4: "آوریل",
    5: "مه",
    6: "ژوئن",
    7: "ژوئیه",
    8: "اوت",
    9: "سپتامبر",
    10: "اکتبر",
    11: "نوامبر",
    12: "دسامبر",
}


@register.filter(name="persian_digits")
def persian_digits(value) -> str:
    """Convert ASCII numerals to Persian numerals (۰-۹)."""
    if value is None:
        return ""
    return str(value).translate(_PERSIAN_DIGIT_MAP)


@register.filter(name="local_num")
def local_num(value) -> str:
    """Render numerals according to the active language (Persian ۰-۹ vs Korean 0-9)."""
    if value is None or value == "":
        return ""
    text = str(value)
    if normalize_lang() == "fa":
        return text.translate(_PERSIAN_DIGIT_MAP)
    return text


@register.filter(name="local_price")
def local_price(value, currency: str = "") -> str:
    """Format decimal prices with thousand separators in the active locale."""
    if value is None or value == "":
        return ""
    try:
        num = float(value)
        formatted = f"{int(num):,}" if num.is_integer() else f"{num:,.2f}"
    except (TypeError, ValueError):
        formatted = str(value)
    if normalize_lang() == "fa":
        formatted = formatted.replace(",", "٬").translate(_PERSIAN_DIGIT_MAP)
    return f"{formatted} {currency}".strip()


@register.filter(name="local_date")
def local_date(value) -> str:
    """Render dates naturally in Persian (fa-IR) and Korean (ko-KR)."""
    if not value:
        return ""
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        dt_date = value.date()
    elif isinstance(value, datetime.date):
        dt_date = value
    else:
        return str(value)

    lang = normalize_lang()
    if lang == "ko":
        return f"{dt_date.year}년 {dt_date.month}월 {dt_date.day}일"
    month_name = _PERSIAN_MONTHS.get(dt_date.month, str(dt_date.month))
    return f"{dt_date.day} {month_name} {dt_date.year}".translate(_PERSIAN_DIGIT_MAP)


@register.filter(name="local_datetime")
def local_datetime(value) -> str:
    """Render date + time in Persian or Korean."""
    if not value:
        return ""
    if isinstance(value, datetime.datetime):
        if timezone.is_aware(value):
            value = timezone.localtime(value)
        date_str = local_date(value)
        time_str = f"{value.hour:02d}:{value.minute:02d}"
        if normalize_lang() == "fa":
            return f"{date_str} — {time_str.translate(_PERSIAN_DIGIT_MAP)}"
        return f"{date_str} {time_str}"
    return local_date(value)


@register.filter(name="accessible_field")
def accessible_field(field):
    """Render a form field with ARIA wiring for server-side validation errors."""
    attrs = {}
    if field.errors:
        attrs["aria-invalid"] = "true"
        attrs["aria-describedby"] = f"{field.auto_id}_error"
    if field.field.required:
        attrs["aria-required"] = "true"
    return field.as_widget(attrs=attrs)


@register.filter(name="tr")
def tr(obj, lang_code: str | None = None):
    """Fetch the localized translation object with automatic language fallback."""
    return resolve_translation(obj, lang_code=lang_code)


@register.filter(name="localized_attr")
def localized_attr(obj, field_base: str) -> str:
    """
    Read `<field_base>_fa` or `<field_base>_ko` on bilingual models with automatic
    fallback to the alternate language.
    """
    if obj is None:
        return ""
    lang = normalize_lang()
    alt = "ko" if lang == "fa" else "fa"
    primary = getattr(obj, f"{field_base}_{lang}", "") or ""
    if primary:
        return primary
    return getattr(obj, f"{field_base}_{alt}", "") or ""


@register.simple_tag(takes_context=True)
def switch_lang_url(context, target_lang: str) -> str:
    request = context.get("request")
    if not request:
        return f"/{target_lang}/"
    return translate_url(request.get_full_path(), target_lang)


@register.simple_tag(takes_context=True)
def query_transform(context, **kwargs) -> str:
    """Preserve existing query parameters while updating specific keys (e.g. page)."""
    request = context.get("request")
    if not request:
        return ""
    updated = request.GET.copy()
    for key, val in kwargs.items():
        if val is None or val == "":
            updated.pop(key, None)
        else:
            updated[key] = str(val)
    encoded = updated.urlencode()
    return f"?{encoded}" if encoded else ""

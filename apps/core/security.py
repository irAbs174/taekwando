"""Security helpers: client IP resolution and cache-backed rate limiting."""
from __future__ import annotations

import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

security_logger = logging.getLogger("techwando.security")


def get_client_ip(request) -> str | None:
    """Extract client IP safely; only trust X-Forwarded-For behind a trusted proxy."""
    if request is None:
        return None
    if getattr(settings, "TRUST_X_FORWARDED_FOR", False):
        xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if xff:
            return xff.split(",")[0].strip()[:45]
    remote_addr = request.META.get("REMOTE_ADDR", "")
    return remote_addr.strip()[:45] or None


def _rate_key(scope: str, identifier: str) -> str:
    digest = hashlib.sha256(identifier.lower().strip().encode("utf-8")).hexdigest()[:32]
    return f"techwando:rl:{scope}:{digest}"


def is_rate_limited(scope: str, identifier: str, max_attempts: int, window_seconds: int) -> bool:
    """Return True when `identifier` has reached `max_attempts` within `window_seconds`."""
    key = _rate_key(scope, identifier)
    count = cache.get(key, 0)
    return int(count) >= int(max_attempts)


def record_rate_limit_hit(scope: str, identifier: str, window_seconds: int) -> int:
    """Increment the rate-limit counter and return the new attempt count."""
    key = _rate_key(scope, identifier)
    added = cache.add(key, 1, timeout=window_seconds)
    if added:
        return 1
    try:
        return int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return 1


def clear_rate_limit(scope: str, identifier: str) -> None:
    """Reset the counter (e.g., after successful authentication)."""
    cache.delete(_rate_key(scope, identifier))

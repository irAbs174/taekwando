"""Audit logging service with safe JSON state serialization."""
from __future__ import annotations

import datetime
from decimal import Decimal

from apps.audit_logs.models import AuditLog
from apps.core.security import get_client_ip


def _sanitize_json(value):
    if isinstance(value, dict):
        return {str(k): _sanitize_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_json(v) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def log_audit_event(
    *,
    actor,
    action: str,
    instance=None,
    target_model: str = "",
    target_id: str = "",
    target_repr: str = "",
    previous_state: dict | None = None,
    new_state: dict | None = None,
    request=None,
) -> AuditLog:
    """Persist an immutable AuditLog entry."""
    resolved_actor = actor if (actor and getattr(actor, "is_authenticated", False)) else None
    actor_email = getattr(resolved_actor, "email", "") if resolved_actor else ""

    if instance is not None:
        meta = instance._meta
        target_model = target_model or f"{meta.app_label}.{meta.model_name}"
        target_id = target_id or (str(instance.pk) if instance.pk is not None else "")
        target_repr = target_repr or str(instance)[:255]

    ip_address = get_client_ip(request)
    user_agent = ""
    if request is not None:
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:300]

    return AuditLog.objects.create(
        actor=resolved_actor,
        actor_email=actor_email,
        action=action[:80],
        target_model=target_model[:120],
        target_id=str(target_id)[:64],
        target_repr=target_repr[:255],
        previous_state=_sanitize_json(previous_state or {}),
        new_state=_sanitize_json(new_state or {}),
        ip_address=ip_address,
        user_agent=user_agent,
    )

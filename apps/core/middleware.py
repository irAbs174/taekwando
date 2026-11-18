"""Security and session integrity middleware."""
from __future__ import annotations

from django.conf import settings
from django.contrib.auth import logout


class ActiveUserAndSecurityHeadersMiddleware:
    """
    1. Immediately invalidates sessions belonging to deactivated accounts.
    2. Applies baseline security headers (Permissions-Policy and CSP).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and not user.is_active:
            logout(request)

        response = self.get_response(request)

        response.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        if "Content-Security-Policy" not in response:
            frame_ancestors = (
                "*"
                if getattr(settings, "DEBUG", False)
                and "django.middleware.clickjacking.XFrameOptionsMiddleware"
                not in settings.MIDDLEWARE
                else "'none'"
            )
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                f"frame-ancestors {frame_ancestors};"
            )
        return response

"""Consistent structured JSON error envelopes for all API responses."""
from __future__ import annotations

from django.core.exceptions import (
    PermissionDenied as DjangoPermissionDenied,
    ValidationError as DjangoValidationError,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def consistent_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
        return Response(
            {
                "error": {
                    "code": "validation_error",
                    "status": status.HTTP_400_BAD_REQUEST,
                    "detail": detail,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if isinstance(exc, DjangoPermissionDenied):
        return Response(
            {
                "error": {
                    "code": "permission_denied",
                    "status": status.HTTP_403_FORBIDDEN,
                    "detail": str(exc) or "You do not have permission to perform this action.",
                }
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    response = exception_handler(exc, context)
    if response is not None:
        code = getattr(exc, "default_code", "api_error")
        response.data = {
            "error": {
                "code": str(code),
                "status": response.status_code,
                "detail": response.data,
            }
        }
    return response

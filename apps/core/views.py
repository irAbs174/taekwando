"""Core views: protected private media delivery, language switching, health check, errors."""
from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.urls import translate_url
from django.utils import translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from apps.core.models import ApprovalStatus
from apps.core.permissions import can_view_private_submission_file
from apps.core.translation_utils import SUPPORTED_LANGUAGES, normalize_lang


def _build_safe_file_response(file_field, *, inline_images: bool = True) -> HttpResponse:
    """
    Deliver a private file safely via Nginx X-Accel-Redirect in production
    or streaming FileResponse with strict anti-sniffing and private cache headers.
    """
    if not file_field or not file_field.name:
        raise Http404

    storage = file_field.storage
    if not storage.exists(file_field.name):
        raise Http404

    file_path = Path(storage.path(file_field.name)).resolve()
    private_root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
    # Prevent any path traversal outside PRIVATE_MEDIA_ROOT
    if private_root not in file_path.parents:
        raise PermissionDenied

    guessed_type, _ = mimetypes.guess_type(file_path.name)
    safe_types = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
    content_type = guessed_type if guessed_type in safe_types else "application/octet-stream"
    disposition = (
        "inline"
        if inline_images and content_type in {"image/jpeg", "image/png", "image/webp", "application/pdf"}
        else "attachment"
    )
    safe_name = file_path.name

    if getattr(settings, "USE_X_ACCEL_REDIRECT", False):
        rel = file_path.relative_to(private_root).as_posix()
        prefix = settings.X_ACCEL_REDIRECT_PREFIX.rstrip("/")
        response = HttpResponse(content_type=content_type)
        response["X-Accel-Redirect"] = f"{prefix}/{rel}"
        response["Content-Disposition"] = f'{disposition}; filename="{safe_name}"'
    else:
        response = FileResponse(
            file_path.open("rb"),
            content_type=content_type,
        )
        response["Content-Disposition"] = f'{disposition}; filename="{safe_name}"'

    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store, max-age=0"
    return response


class ProtectedSubmissionFileView(LoginRequiredMixin, View):
    """
    Serve sensitive certificates, medal evidence, and private activity photographs
    ONLY to the owning member or authorized reviewers.
    """

    def get(self, request, model_type: str, pk: int):
        from apps.achievements.models import Achievement
        from apps.activities.models import SocialActivity
        from apps.belts.models import BeltHistory
        from apps.competitions.models import CompetitionParticipation
        from apps.medals.models import Medal

        registry = {
            "achievement": (Achievement, "certificate"),
            "belt": (BeltHistory, "certificate"),
            "medal": (Medal, "evidence"),
            "activity": (SocialActivity, "photograph"),
            "competition": (CompetitionParticipation, "certificate"),
        }
        entry = registry.get(model_type)
        if not entry:
            raise Http404

        model_cls, field_name = entry
        submission = get_object_or_404(
            model_cls.objects.select_related("member", "member__user"),
            pk=pk,
        )
        if not can_view_private_submission_file(request.user, submission):
            raise PermissionDenied

        file_field = getattr(submission, field_name, None)
        return _build_safe_file_response(file_field)


class PublicActivityPhotoView(View):
    """
    Serve a SocialActivity photograph publicly ONLY when the activity is APPROVED,
    the member granted public_visibility_consent, and the member profile is publicly
    eligible; otherwise permit only the owning member or authorized moderators.
    """

    def get(self, request, pk: int):
        from apps.activities.models import SocialActivity

        activity = get_object_or_404(
            SocialActivity.objects.select_related("member", "member__user"),
            pk=pk,
        )
        is_publicly_eligible = (
            activity.approval_status == ApprovalStatus.APPROVED
            and activity.public_visibility_consent
            and activity.member.is_publicly_visible
        )
        if not is_publicly_eligible:
            if not can_view_private_submission_file(request.user, activity):
                raise Http404
        response = _build_safe_file_response(activity.photograph, inline_images=True)
        if is_publicly_eligible:
            response["Cache-Control"] = "public, max-age=3600"
        return response


class BlockedPrivateMediaPathView(View):
    """Always deny direct guessed access to /media/certificates/* or /media/medals/*."""

    def get(self, request, *args, **kwargs):
        raise PermissionDenied


class RootLanguageRedirectView(View):
    """Redirect bare `/` to the user's preferred localized homepage (`/fa/` or `/ko/`)."""

    def get(self, request):
        lang = normalize_lang(getattr(request, "LANGUAGE_CODE", None))
        return HttpResponseRedirect(f"/{lang}/")


class SwitchLanguageView(View):
    """Switch interface and route language between Persian (fa) and Korean (ko)."""

    def post(self, request):
        lang = (request.POST.get("language") or "").strip().lower()
        next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
        return self._switch(request, lang, next_url)

    def get(self, request, lang_code: str):
        next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or "/"
        return self._switch(request, lang_code.lower(), next_url)

    def _switch(self, request, lang: str, next_url: str) -> HttpResponseRedirect:
        if lang not in SUPPORTED_LANGUAGES:
            lang = settings.LANGUAGE_CODE

        if not url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = f"/{lang}/"

        translated = translate_url(next_url, lang)
        # Ensure prefix matches selected language for localized public/portal routes
        other = "ko" if lang == "fa" else "fa"
        if translated.startswith(f"/{other}/"):
            translated = f"/{lang}/{translated[len(other) + 2:]}"
        elif translated == "/":
            translated = f"/{lang}/"

        translation.activate(lang)
        if request.user.is_authenticated and getattr(request.user, "preferred_language", None) != lang:
            request.user.preferred_language = lang
            request.user.save(update_fields=["preferred_language"])

        response = HttpResponseRedirect(translated)
        response.set_cookie(
            settings.LANGUAGE_COOKIE_NAME,
            lang,
            max_age=settings.LANGUAGE_COOKIE_AGE,
            path="/",
            secure=getattr(settings, "LANGUAGE_COOKIE_SECURE", False),
            httponly=getattr(settings, "LANGUAGE_COOKIE_HTTPONLY", True),
            samesite=getattr(settings, "LANGUAGE_COOKIE_SAMESITE", "Lax"),
        )
        return response


class HealthCheckView(View):
    """Lightweight liveness/readiness endpoint for container and reverse-proxy checks."""

    def get(self, request):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "service": "teakwondo"})


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)

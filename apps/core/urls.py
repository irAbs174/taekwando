"""Non-prefixed core utility endpoints (protected media, language switch, health)."""
from django.urls import path

from apps.core.views import (
    HealthCheckView,
    ProtectedSubmissionFileView,
    PublicActivityPhotoView,
    SwitchLanguageView,
)

app_name = "core"

urlpatterns = [
    path("healthz/", HealthCheckView.as_view(), name="healthz"),
    path("switch-language/", SwitchLanguageView.as_view(), name="switch_language"),
    path(
        "switch-language/<str:lang_code>/",
        SwitchLanguageView.as_view(),
        name="switch_language_get",
    ),
    path(
        "protected-media/<str:model_type>/<int:pk>/",
        ProtectedSubmissionFileView.as_view(),
        name="protected_file",
    ),
    path(
        "activity-photo/<int:pk>/",
        PublicActivityPhotoView.as_view(),
        name="activity_photo",
    ),
]

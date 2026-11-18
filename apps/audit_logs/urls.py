"""URL patterns for audit and moderation history in the admin dashboard."""
from django.urls import path

from apps.audit_logs.views import AuditLogListView, ReviewLogListView

app_name = "audit_logs"

urlpatterns = [
    path("", AuditLogListView.as_view(), name="list"),
    path("reviews/", ReviewLogListView.as_view(), name="reviews"),
]

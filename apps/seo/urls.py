"""Admin portal routes for SEO management."""
from django.urls import path

from apps.seo.views import AdminSEOCreateView, AdminSEOListView, AdminSEOUpdateView

app_name = "seo"

urlpatterns = [
    path("", AdminSEOListView.as_view(), name="admin_list"),
    path("add/", AdminSEOCreateView.as_view(), name="admin_add"),
    path("<int:pk>/edit/", AdminSEOUpdateView.as_view(), name="admin_edit"),
]

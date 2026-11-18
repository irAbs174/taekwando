"""URL routes for belt history in the member portal and admin belt management."""
from django.urls import path

from apps.belts.views import (
    AdminBeltTypeCreateView,
    AdminBeltTypeListView,
    AdminBeltTypeUpdateView,
    MemberBeltCorrectionView,
    MemberBeltCreateView,
    MemberBeltDeleteView,
    MemberBeltDetailView,
    MemberBeltListView,
    MemberBeltUpdateView,
)

app_name = "belts"

urlpatterns = [
    path("", MemberBeltListView.as_view(), name="member_list"),
    path("add/", MemberBeltCreateView.as_view(), name="member_add"),
    path("<int:pk>/", MemberBeltDetailView.as_view(), name="member_detail"),
    path("<int:pk>/edit/", MemberBeltUpdateView.as_view(), name="member_edit"),
    path("<int:pk>/delete/", MemberBeltDeleteView.as_view(), name="member_delete"),
    path(
        "<int:pk>/request-correction/",
        MemberBeltCorrectionView.as_view(),
        name="member_correction",
    ),
    path("admin-types/", AdminBeltTypeListView.as_view(), name="admin_type_list"),
    path("admin-types/add/", AdminBeltTypeCreateView.as_view(), name="admin_type_add"),
    path(
        "admin-types/<int:pk>/edit/",
        AdminBeltTypeUpdateView.as_view(),
        name="admin_type_edit",
    ),
]

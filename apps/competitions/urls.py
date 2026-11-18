"""Routes for member competition participations and admin competition CRUD."""
from django.urls import path

from apps.competitions.views import (
    AdminCompetitionCreateView,
    AdminCompetitionListView,
    AdminCompetitionUpdateView,
    MemberCompetitionCorrectionView,
    MemberCompetitionCreateView,
    MemberCompetitionDeleteView,
    MemberCompetitionDetailView,
    MemberCompetitionListView,
    MemberCompetitionUpdateView,
)

app_name = "competitions"

urlpatterns = [
    path("", MemberCompetitionListView.as_view(), name="member_list"),
    path("add/", MemberCompetitionCreateView.as_view(), name="member_add"),
    path("<int:pk>/", MemberCompetitionDetailView.as_view(), name="member_detail"),
    path("<int:pk>/edit/", MemberCompetitionUpdateView.as_view(), name="member_edit"),
    path("<int:pk>/delete/", MemberCompetitionDeleteView.as_view(), name="member_delete"),
    path(
        "<int:pk>/request-correction/",
        MemberCompetitionCorrectionView.as_view(),
        name="member_correction",
    ),
    path("manage/", AdminCompetitionListView.as_view(), name="admin_list"),
    path("manage/add/", AdminCompetitionCreateView.as_view(), name="admin_add"),
    path("manage/<int:pk>/edit/", AdminCompetitionUpdateView.as_view(), name="admin_edit"),
]

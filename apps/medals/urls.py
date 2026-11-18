"""Member portal URLs for medals."""
from django.urls import path

from apps.medals.views import (
    MemberMedalCorrectionView,
    MemberMedalCreateView,
    MemberMedalDeleteView,
    MemberMedalDetailView,
    MemberMedalListView,
    MemberMedalUpdateView,
)

app_name = "medals"

urlpatterns = [
    path("", MemberMedalListView.as_view(), name="member_list"),
    path("add/", MemberMedalCreateView.as_view(), name="member_add"),
    path("<int:pk>/", MemberMedalDetailView.as_view(), name="member_detail"),
    path("<int:pk>/edit/", MemberMedalUpdateView.as_view(), name="member_edit"),
    path("<int:pk>/delete/", MemberMedalDeleteView.as_view(), name="member_delete"),
    path(
        "<int:pk>/request-correction/",
        MemberMedalCorrectionView.as_view(),
        name="member_correction",
    ),
]

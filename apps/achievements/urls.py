"""Member portal URLs for achievements."""
from django.urls import path

from apps.achievements.views import (
    MemberAchievementCorrectionView,
    MemberAchievementCreateView,
    MemberAchievementDeleteView,
    MemberAchievementDetailView,
    MemberAchievementListView,
    MemberAchievementUpdateView,
)

app_name = "achievements"

urlpatterns = [
    path("", MemberAchievementListView.as_view(), name="member_list"),
    path("add/", MemberAchievementCreateView.as_view(), name="member_add"),
    path("<int:pk>/", MemberAchievementDetailView.as_view(), name="member_detail"),
    path("<int:pk>/edit/", MemberAchievementUpdateView.as_view(), name="member_edit"),
    path("<int:pk>/delete/", MemberAchievementDeleteView.as_view(), name="member_delete"),
    path(
        "<int:pk>/request-correction/",
        MemberAchievementCorrectionView.as_view(),
        name="member_correction",
    ),
]

"""Member portal URLs for social activities."""
from django.urls import path

from apps.activities.views import (
    MemberActivityCorrectionView,
    MemberActivityCreateView,
    MemberActivityDeleteView,
    MemberActivityDetailView,
    MemberActivityListView,
    MemberActivityUpdateView,
)

app_name = "activities"

urlpatterns = [
    path("", MemberActivityListView.as_view(), name="member_list"),
    path("add/", MemberActivityCreateView.as_view(), name="member_add"),
    path("<int:pk>/", MemberActivityDetailView.as_view(), name="member_detail"),
    path("<int:pk>/edit/", MemberActivityUpdateView.as_view(), name="member_edit"),
    path("<int:pk>/delete/", MemberActivityDeleteView.as_view(), name="member_delete"),
    path(
        "<int:pk>/request-correction/",
        MemberActivityCorrectionView.as_view(),
        name="member_correction",
    ),
]

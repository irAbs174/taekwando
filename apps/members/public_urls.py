"""Public Champions & Honors URL routes (mounted under /<lang>/champions/)."""
from django.urls import path

from apps.members.views import (
    PublicBeltAchievementsView,
    PublicChampionDetailView,
    PublicChampionsListView,
    PublicCompetitionResultsView,
    PublicMedalWinnersView,
)

app_name = "champions"

urlpatterns = [
    path("", PublicChampionsListView.as_view(), name="list"),
    path("medals/", PublicMedalWinnersView.as_view(), name="medals"),
    path("belts/", PublicBeltAchievementsView.as_view(), name="belts"),
    path("competitions/", PublicCompetitionResultsView.as_view(), name="competitions"),
    path("<slug:slug>/", PublicChampionDetailView.as_view(), name="detail"),
]

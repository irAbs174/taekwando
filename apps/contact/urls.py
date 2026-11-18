"""Contact page and admin contact management URLs."""
from django.urls import path

from apps.contact.views import (
    AdminContactDetailView,
    AdminContactListView,
    PublicContactView,
)

app_name = "contact"

urlpatterns = [
    path("", PublicContactView.as_view(), name="public"),
    path("manage/", AdminContactListView.as_view(), name="admin_list"),
    path("manage/<int:pk>/", AdminContactDetailView.as_view(), name="admin_detail"),
]

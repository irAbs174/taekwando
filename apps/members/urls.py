"""Private Club Member Portal URL routes (mounted under /<lang>/member/)."""
from django.urls import path

from apps.accounts.views import AccountSettingsView, MemberPasswordChangeView
from apps.members.views import MemberDashboardView, MemberProfileEditView

app_name = "members"

urlpatterns = [
    path("dashboard/", MemberDashboardView.as_view(), name="dashboard"),
    path("profile/", MemberProfileEditView.as_view(), name="profile_edit"),
    path("settings/", AccountSettingsView.as_view(), name="account_settings"),
    path("settings/password/", MemberPasswordChangeView.as_view(), name="password_change"),
]

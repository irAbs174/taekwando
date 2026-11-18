"""Authentication and custom administration portal URL routes."""
from django.urls import path

from apps.accounts.views import (
    AdminDashboardView,
    AdminMemberCreateView,
    AdminMemberDetailView,
    AdminMemberListView,
    MemberPasswordResetCompleteView,
    MemberPasswordResetConfirmView,
    MemberPasswordResetDoneView,
    MemberPasswordResetView,
    MemberRegisterView,
    ModerationQueueView,
    PostLoginRedirectView,
    RateLimitedLoginView,
    ReviewSubmissionView,
    SafeLogoutView,
)

app_name = "accounts"

urlpatterns = [
    # Public authentication
    path("login/", RateLimitedLoginView.as_view(), name="login"),
    path("register/", MemberRegisterView.as_view(), name="register"),
    path("logout/", SafeLogoutView.as_view(), name="logout"),
    path("redirect/", PostLoginRedirectView.as_view(), name="post_login_redirect"),
    # Password reset flow
    path("password-reset/", MemberPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        MemberPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        MemberPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password-reset/complete/",
        MemberPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    # Custom administration portal
    path("management/", AdminDashboardView.as_view(), name="admin_dashboard"),
    path(
        "management/moderation/",
        ModerationQueueView.as_view(),
        name="admin_moderation_queue",
    ),
    path(
        "management/moderation/<str:model_type>/<int:pk>/",
        ReviewSubmissionView.as_view(),
        name="admin_review_submission",
    ),
    path("management/members/", AdminMemberListView.as_view(), name="admin_member_list"),
    path(
        "management/members/add/",
        AdminMemberCreateView.as_view(),
        name="admin_member_add",
    ),
    path(
        "management/members/<int:pk>/",
        AdminMemberDetailView.as_view(),
        name="admin_member_detail",
    ),
]

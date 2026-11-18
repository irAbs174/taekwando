"""Versioned /api/v1/ URL routing and drf-spectacular OpenAPI schema/docs."""
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from apps.api.views import (
    AdminAchievementModerationViewSet,
    AdminActivityModerationViewSet,
    AdminBeltModerationViewSet,
    AdminMedalModerationViewSet,
    AdminMemberViewSet,
    AdminPageViewSet,
    AdminPostViewSet,
    AdminProductViewSet,
    CurrentMemberProfileAPIView,
    MemberAchievementViewSet,
    MemberActivityViewSet,
    MemberBeltViewSet,
    MemberMedalViewSet,
    MemberNotificationViewSet,
    PublicBlogViewSet,
    PublicChampionViewSet,
    PublicContactCreateAPIView,
    PublicMedalWinnerViewSet,
    PublicPageViewSet,
    PublicProductViewSet,
)

app_name = "api"

public_router = DefaultRouter()
public_router.register("blog", PublicBlogViewSet, basename="public-blog")
public_router.register("products", PublicProductViewSet, basename="public-products")
public_router.register("champions", PublicChampionViewSet, basename="public-champions")
public_router.register("medals", PublicMedalWinnerViewSet, basename="public-medals")
public_router.register("pages", PublicPageViewSet, basename="public-pages")

member_router = DefaultRouter()
member_router.register("achievements", MemberAchievementViewSet, basename="member-achievements")
member_router.register("medals", MemberMedalViewSet, basename="member-medals")
member_router.register("belts", MemberBeltViewSet, basename="member-belts")
member_router.register("activities", MemberActivityViewSet, basename="member-activities")
member_router.register(
    "notifications", MemberNotificationViewSet, basename="member-notifications"
)

admin_router = DefaultRouter()
admin_router.register("members", AdminMemberViewSet, basename="admin-members")
admin_router.register("medals", AdminMedalModerationViewSet, basename="admin-medals")
admin_router.register(
    "achievements", AdminAchievementModerationViewSet, basename="admin-achievements"
)
admin_router.register("belts", AdminBeltModerationViewSet, basename="admin-belts")
admin_router.register("activities", AdminActivityModerationViewSet, basename="admin-activities")
admin_router.register("posts", AdminPostViewSet, basename="admin-posts")
admin_router.register("products", AdminProductViewSet, basename="admin-products")
admin_router.register("pages", AdminPageViewSet, basename="admin-pages")

urlpatterns = [
    # OpenAPI schema & interactive documentation
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api:schema"), name="swagger-ui"),
    path("redoc/", SpectacularRedocView.as_view(url_name="api:schema"), name="redoc"),
    # Public API
    path("public/contact/", PublicContactCreateAPIView.as_view(), name="public-contact"),
    path("public/", include(public_router.urls)),
    # Authenticated Member API
    path("member/profile/", CurrentMemberProfileAPIView.as_view(), name="member-profile"),
    path("member/", include(member_router.urls)),
    # Authorized Admin API
    path("admin/", include(admin_router.urls)),
]

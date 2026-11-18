"""DRF ViewSets and API views for public, member, and admin /api/v1/ namespaces."""
from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.api.permissions import (
    IsActiveAuthenticated,
    IsClubManagerAPI,
    IsContentAdminAPI,
    IsOwnMemberObject,
    IsSubmissionModeratorAPI,
)
from apps.api.serializers import (
    AdminAchievementModerationSerializer,
    AdminActivityModerationSerializer,
    AdminBeltModerationSerializer,
    AdminMedalModerationSerializer,
    AdminMemberSerializer,
    AdminMembershipDecisionSerializer,
    AdminPageSerializer,
    AdminPostSerializer,
    AdminProductSerializer,
    AdminReviewDecisionSerializer,
    CorrectionRequestAPISerializer,
    CurrentMemberProfileSerializer,
    MemberAchievementSerializer,
    MemberActivitySerializer,
    MemberBeltHistorySerializer,
    MemberMedalSerializer,
    MemberNotificationSerializer,
    PublicChampionDetailSerializer,
    PublicChampionListSerializer,
    PublicContactSerializer,
    PublicMedalSerializer,
    PublicPageSerializer,
    PublicPostDetailSerializer,
    PublicPostListSerializer,
    PublicProductSerializer,
)
from apps.audit_logs.services import log_audit_event
from apps.belts.models import BeltHistory
from apps.blog.models import Post
from apps.contact.services import ContactService
from apps.core.models import ApprovalStatus
from apps.core.services import ModerationService
from apps.medals.models import Medal
from apps.members.models import MemberProfile
from apps.members.services import ensure_member_profile, review_membership_application
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.pages.models import Page
from apps.products.models import Product


# =============================================================================
# Public API ViewSets
# =============================================================================


class PublicBlogViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_fields = ["category__slug", "tags__slug", "is_featured"]
    search_fields = ["translations__title", "translations__excerpt", "translations__body"]
    ordering_fields = ["published_at", "created_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        return (
            Post.objects.published()
            .select_related("category")
            .prefetch_related("translations", "category__translations", "tags")
            .distinct()
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicPostDetailSerializer
        return PublicPostListSerializer


class PublicProductViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicProductSerializer
    lookup_field = "slug"
    filterset_fields = ["category__slug", "discipline", "is_available", "is_featured"]
    search_fields = ["sku", "translations__name", "translations__description"]
    ordering_fields = ["price", "created_at"]
    ordering = ["-is_featured", "-created_at"]

    def get_queryset(self):
        return (
            Product.objects.published()
            .select_related("category")
            .prefetch_related("translations", "category__translations", "images")
            .distinct()
        )


class PublicPageViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicPageSerializer
    lookup_field = "slug"
    filterset_fields = ["page_type"]
    search_fields = ["translations__title", "translations__body"]

    def get_queryset(self):
        return Page.objects.published().prefetch_related("translations").distinct()


class PublicChampionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_fields = ["primary_discipline"]
    search_fields = ["first_name", "last_name", "first_name_ja", "last_name_ja"]
    ordering_fields = ["joining_date", "approved_medal_count"]

    def get_queryset(self):
        qs = MemberProfile.objects.publicly_visible().annotate(
            approved_medal_count=Count(
                "medals",
                filter=Q(medals__approval_status=ApprovalStatus.APPROVED),
                distinct=True,
            )
        )
        medal_type = self.request.query_params.get("medal_type")
        belt_id = self.request.query_params.get("belt")
        competition_id = self.request.query_params.get("competition")
        if medal_type:
            qs = qs.filter(
                medals__approval_status=ApprovalStatus.APPROVED,
                medals__medal_type=medal_type,
            )
        if belt_id and belt_id.isdigit():
            qs = qs.filter(
                belt_histories__approval_status=ApprovalStatus.APPROVED,
                belt_histories__belt_type_id=int(belt_id),
            )
        if competition_id and competition_id.isdigit():
            qs = qs.filter(
                medals__approval_status=ApprovalStatus.APPROVED,
                medals__competition_id=int(competition_id),
            )
        return qs.distinct().order_by("-approved_medal_count", "last_name")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PublicChampionDetailSerializer
        return PublicChampionListSerializer


class PublicMedalWinnerViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = PublicMedalSerializer
    filterset_fields = ["medal_type", "discipline", "competition"]
    search_fields = [
        "member__first_name",
        "member__last_name",
        "competition_name",
        "competition_name_ja",
    ]
    ordering_fields = ["award_date"]
    ordering = ["-award_date"]

    def get_queryset(self):
        return Medal.objects.publicly_visible().select_related("member", "competition")


class PublicContactCreateAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = PublicContactSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "contact"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = ContactService.submit_message(
            name=serializer.validated_data["name"],
            email=serializer.validated_data["email"],
            subject=serializer.validated_data["subject"],
            message=serializer.validated_data["message"],
            language=serializer.validated_data.get("language") or request.LANGUAGE_CODE,
            request=request,
        )
        return Response(
            {"id": entry.id, "detail": "Contact message received."},
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Authenticated Member API ViewSets (strictly scoped to own MemberProfile)
# =============================================================================


class CurrentMemberProfileAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsActiveAuthenticated]
    serializer_class = CurrentMemberProfileSerializer

    def get_object(self) -> MemberProfile:
        return ensure_member_profile(self.request.user)

    def perform_update(self, serializer):
        profile = serializer.save()
        user = profile.user
        if user.first_name != profile.first_name or user.last_name != profile.last_name:
            user.first_name = profile.first_name
            user.last_name = profile.last_name
            user.save(update_fields=["first_name", "last_name", "updated_at"])
        log_audit_event(
            actor=self.request.user,
            action="API_MEMBER_PROFILE_UPDATED",
            instance=profile,
            request=self.request,
        )


class BaseMemberSubmissionViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet enforcing strict object ownership, server-set member identity,
    mandatory PENDING workflow, and immutable moderation fields.
    """

    permission_classes = [IsActiveAuthenticated, IsOwnMemberObject]
    filterset_fields = ["approval_status"]

    def get_member(self) -> MemberProfile:
        return ensure_member_profile(self.request.user)

    def perform_create(self, serializer):
        member = self.get_member()
        extra = {"member": member, "approval_status": ApprovalStatus.PENDING}
        if serializer.Meta.model is BeltHistory:
            extra["discipline"] = serializer.validated_data["belt_type"].discipline
        instance = serializer.save(**extra)
        ModerationService.record_member_submission(
            instance, actor=self.request.user, is_resubmission=False, request=self.request
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        if not instance.can_member_edit:
            raise PermissionDenied(
                "Approved or rejected records cannot be modified directly. Submit a correction request first."
            )
        extra = {}
        if serializer.Meta.model is BeltHistory and "belt_type" in serializer.validated_data:
            extra["discipline"] = serializer.validated_data["belt_type"].discipline
        updated = serializer.save(**extra)
        ModerationService.record_member_submission(
            updated, actor=self.request.user, is_resubmission=True, request=self.request
        )

    def perform_destroy(self, instance):
        if not instance.can_member_delete:
            raise PermissionDenied("Approved submissions cannot be deleted by members.")
        log_audit_event(
            actor=self.request.user,
            action="API_SUBMISSION_DELETED",
            instance=instance,
            request=self.request,
        )
        instance.delete()

    @action(detail=True, methods=["post"], serializer_class=CorrectionRequestAPISerializer)
    def request_correction(self, request, pk=None):
        instance = self.get_object()
        if not instance.can_request_correction:
            raise PermissionDenied("This record can already be edited directly.")
        ser = CorrectionRequestAPISerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ModerationService.request_correction(
            instance,
            actor=request.user,
            reason=ser.validated_data["reason"],
            request=request,
        )
        return Response(
            {"detail": "Correction request submitted.", "approval_status": instance.approval_status}
        )


class MemberAchievementViewSet(BaseMemberSubmissionViewSet):
    serializer_class = MemberAchievementSerializer
    queryset = Achievement.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Achievement.objects.none()
        return Achievement.objects.filter(member=self.get_member()).select_related("competition")


class MemberMedalViewSet(BaseMemberSubmissionViewSet):
    serializer_class = MemberMedalSerializer
    queryset = Medal.objects.none()
    filterset_fields = ["approval_status", "medal_type", "discipline"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Medal.objects.none()
        return Medal.objects.filter(member=self.get_member()).select_related("competition")


class MemberBeltViewSet(BaseMemberSubmissionViewSet):
    serializer_class = MemberBeltHistorySerializer
    queryset = BeltHistory.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return BeltHistory.objects.none()
        return BeltHistory.objects.filter(member=self.get_member()).select_related("belt_type")


class MemberActivityViewSet(BaseMemberSubmissionViewSet):
    serializer_class = MemberActivitySerializer
    queryset = SocialActivity.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return SocialActivity.objects.none()
        return SocialActivity.objects.filter(member=self.get_member())


class MemberNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsActiveAuthenticated, IsOwnMemberObject]
    serializer_class = MemberNotificationSerializer
    queryset = Notification.objects.none()
    filterset_fields = ["is_read", "notification_type"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        NotificationService.mark_as_read(notif, request.user)
        return Response({"id": notif.id, "is_read": True})

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        updated = NotificationService.mark_all_as_read(request.user)
        return Response({"marked_read": updated})


# =============================================================================
# Admin Moderation & Content Management API ViewSets
# =============================================================================


class AdminMemberViewSet(viewsets.ModelViewSet):
    permission_classes = [IsClubManagerAPI]
    serializer_class = AdminMemberSerializer
    queryset = MemberProfile.objects.select_related("user").order_by("-joining_date")
    filterset_fields = ["membership_status", "primary_discipline", "public_profile_visibility"]
    search_fields = ["membership_number", "first_name", "last_name", "user__email"]
    http_method_names = ["get", "patch", "put", "post", "head", "options"]

    def create(self, request, *args, **kwargs):
        return Response(
            {"error": {"code": "method_not_allowed", "status": 405, "detail": "Use admin user creation form."}},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], serializer_class=AdminMembershipDecisionSerializer)
    def review(self, request, pk=None):
        profile = self.get_object()
        ser = AdminMembershipDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        review_membership_application(
            profile=profile,
            reviewer=request.user,
            new_status=ser.validated_data["membership_status"],
            note=ser.validated_data.get("admin_note", ""),
            request=request,
        )
        return Response(AdminMemberSerializer(profile).data)


class BaseAdminModerationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsSubmissionModeratorAPI]
    moderation_model_key: str = ""
    filterset_fields = ["approval_status", "member"]

    @action(detail=True, methods=["post"], serializer_class=AdminReviewDecisionSerializer)
    def review(self, request, pk=None):
        submission = self.get_object()
        ser = AdminReviewDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ModerationService.review_submission(
            submission,
            reviewer=request.user,
            new_status=ser.validated_data["approval_status"],
            note=ser.validated_data.get("admin_note", ""),
            request=request,
        )
        return Response(self.get_serializer(submission).data)


class AdminMedalModerationViewSet(BaseAdminModerationViewSet):
    moderation_model_key = "medal"
    serializer_class = AdminMedalModerationSerializer
    queryset = Medal.objects.select_related("member", "competition").order_by("-created_at")


class AdminAchievementModerationViewSet(BaseAdminModerationViewSet):
    moderation_model_key = "achievement"
    serializer_class = AdminAchievementModerationSerializer
    queryset = Achievement.objects.select_related("member", "competition").order_by("-created_at")


class AdminBeltModerationViewSet(BaseAdminModerationViewSet):
    moderation_model_key = "belthistory"
    serializer_class = AdminBeltModerationSerializer
    queryset = BeltHistory.objects.select_related("member", "belt_type").order_by("-created_at")


class AdminActivityModerationViewSet(BaseAdminModerationViewSet):
    moderation_model_key = "socialactivity"
    serializer_class = AdminActivityModerationSerializer
    queryset = SocialActivity.objects.select_related("member").order_by("-created_at")


class AdminPostViewSet(viewsets.ModelViewSet):
    permission_classes = [IsContentAdminAPI]
    serializer_class = AdminPostSerializer
    queryset = Post.objects.prefetch_related("translations", "tags").order_by("-created_at")
    filterset_fields = ["status", "category", "is_featured"]

    def perform_create(self, serializer):
        post = serializer.save(author=self.request.user)
        log_audit_event(
            actor=self.request.user,
            action="API_POST_CREATED",
            instance=post,
            request=self.request,
        )

    def perform_update(self, serializer):
        post = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="API_POST_UPDATED",
            instance=post,
            request=self.request,
        )


class AdminProductViewSet(viewsets.ModelViewSet):
    permission_classes = [IsContentAdminAPI]
    serializer_class = AdminProductSerializer
    queryset = Product.objects.prefetch_related("translations").order_by("-created_at")
    filterset_fields = ["status", "category", "discipline", "is_available"]

    def perform_create(self, serializer):
        product = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="API_PRODUCT_CREATED",
            instance=product,
            request=self.request,
        )

    def perform_update(self, serializer):
        product = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="API_PRODUCT_UPDATED",
            instance=product,
            request=self.request,
        )


class AdminPageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsContentAdminAPI]
    serializer_class = AdminPageSerializer
    queryset = Page.objects.prefetch_related("translations").order_by("display_order", "slug")
    filterset_fields = ["status", "page_type"]

    def perform_create(self, serializer):
        page = serializer.save()
        log_audit_event(
            actor=self.request.user,
            action="API_PAGE_CREATED",
            instance=page,
            request=self.request,
        )

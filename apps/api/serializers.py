"""ModelSerializers for public, authenticated member, and admin API endpoints."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.belts.models import BeltHistory, BeltType
from apps.blog.models import Category, Post, PostTranslation, Tag
from apps.competitions.models import Competition
from apps.contact.models import ContactMessage
from apps.core.models import ApprovalStatus
from apps.core.translation_utils import normalize_lang
from apps.medals.models import Medal
from apps.members.models import MemberProfile, MembershipStatus
from apps.notifications.models import Notification
from apps.pages.models import Page, PageTranslation
from apps.products.models import Product, ProductCategory, ProductImage, ProductTranslation


def _req_lang(serializer: serializers.Serializer) -> str:
    request = serializer.context.get("request")
    if request:
        q_lang = request.query_params.get("lang")
        if q_lang in {"fa", "ko"}:
            return q_lang
        return normalize_lang(getattr(request, "LANGUAGE_CODE", None))
    return normalize_lang()


# =============================================================================
# Public Read-Only & Contact Serializers (strictly zero private fields)
# =============================================================================


class TagSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Tag
        fields = ["slug", "name", "name_fa", "name_ko"]

    def get_name(self, obj: Tag) -> str:
        return (obj.name_ko or obj.name_fa) if _req_lang(self) == "ko" else obj.name_fa


class PublicBlogCategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["slug", "name"]

    def get_name(self, obj: Category) -> str:
        tr = obj.get_translation(_req_lang(self))
        return tr.name if tr else obj.slug


class PublicPostListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    excerpt = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    is_fallback = serializers.SerializerMethodField()
    category = PublicBlogCategorySerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "slug",
            "title",
            "excerpt",
            "language",
            "is_fallback",
            "category",
            "tags",
            "featured_image",
            "is_featured",
            "published_at",
        ]

    def _tr(self, obj: Post):
        return obj.get_translation(_req_lang(self))

    def get_title(self, obj: Post) -> str:
        tr = self._tr(obj)
        return tr.title if tr else obj.slug

    def get_excerpt(self, obj: Post) -> str:
        tr = self._tr(obj)
        return tr.excerpt if tr else ""

    def get_language(self, obj: Post) -> str:
        tr = self._tr(obj)
        return tr.language if tr else _req_lang(self)

    def get_is_fallback(self, obj: Post) -> bool:
        tr = self._tr(obj)
        return bool(getattr(tr, "is_fallback", False)) if tr else False


class PublicPostDetailSerializer(PublicPostListSerializer):
    body = serializers.SerializerMethodField()
    seo_title = serializers.SerializerMethodField()
    seo_description = serializers.SerializerMethodField()

    class Meta(PublicPostListSerializer.Meta):
        fields = PublicPostListSerializer.Meta.fields + ["body", "seo_title", "seo_description"]

    def get_body(self, obj: Post) -> str:
        tr = self._tr(obj)
        return tr.body if tr else ""

    def get_seo_title(self, obj: Post) -> str:
        tr = self._tr(obj)
        return (tr.seo_title or tr.title) if tr else obj.slug

    def get_seo_description(self, obj: Post) -> str:
        tr = self._tr(obj)
        return (tr.seo_description or tr.excerpt) if tr else ""


class ProductImageSerializer(serializers.ModelSerializer):
    alt = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "image", "alt", "is_primary", "display_order"]

    def get_alt(self, obj: ProductImage) -> str:
        return obj.alt_text_ko if _req_lang(self) == "ko" and obj.alt_text_ko else obj.alt_text_fa


class PublicProductCategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = ProductCategory
        fields = ["slug", "name"]

    def get_name(self, obj: ProductCategory) -> str:
        tr = obj.get_translation(_req_lang(self))
        return tr.name if tr else obj.slug


class PublicProductSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    short_description = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    specifications = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()
    category = PublicProductCategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            "slug",
            "sku",
            "name",
            "short_description",
            "description",
            "specifications",
            "language",
            "category",
            "discipline",
            "price",
            "currency",
            "is_available",
            "is_featured",
            "images",
        ]

    def _tr(self, obj: Product):
        return obj.get_translation(_req_lang(self))

    def get_name(self, obj: Product) -> str:
        tr = self._tr(obj)
        return tr.name if tr else obj.slug

    def get_short_description(self, obj: Product) -> str:
        tr = self._tr(obj)
        return tr.short_description if tr else ""

    def get_description(self, obj: Product) -> str:
        tr = self._tr(obj)
        return tr.description if tr else ""

    def get_specifications(self, obj: Product) -> str:
        tr = self._tr(obj)
        return tr.specifications if tr else ""

    def get_language(self, obj: Product) -> str:
        tr = self._tr(obj)
        return tr.language if tr else _req_lang(self)


class PublicPageSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    subtitle = serializers.SerializerMethodField()
    summary = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    language = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = ["slug", "page_type", "title", "subtitle", "summary", "body", "language"]

    def _tr(self, obj: Page):
        return obj.get_translation(_req_lang(self))

    def get_title(self, obj: Page) -> str:
        tr = self._tr(obj)
        return tr.title if tr else obj.slug

    def get_subtitle(self, obj: Page) -> str:
        tr = self._tr(obj)
        return tr.subtitle if tr else ""

    def get_summary(self, obj: Page) -> str:
        tr = self._tr(obj)
        return tr.summary if tr else ""

    def get_body(self, obj: Page) -> str:
        tr = self._tr(obj)
        return tr.body if tr else ""

    def get_language(self, obj: Page) -> str:
        tr = self._tr(obj)
        return tr.language if tr else _req_lang(self)


class BeltTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeltType
        fields = [
            "id",
            "discipline",
            "name_fa",
            "name_ko",
            "rank_code",
            "rank_order",
            "color_hex",
            "is_black_belt",
        ]


class PublicMedalSerializer(serializers.ModelSerializer):
    """Exposes ONLY public medal attributes — never evidence files or admin notes."""

    athlete_name = serializers.SerializerMethodField()
    athlete_slug = serializers.CharField(source="member.slug", read_only=True)
    competition_display = serializers.SerializerMethodField()
    location_display = serializers.SerializerMethodField()

    class Meta:
        model = Medal
        fields = [
            "id",
            "athlete_name",
            "athlete_slug",
            "medal_type",
            "discipline",
            "competition_display",
            "location_display",
            "division_category",
            "award_date",
        ]

    def get_athlete_name(self, obj: Medal) -> str:
        m = obj.member
        if _req_lang(self) == "ko" and (m.last_name_ko or m.first_name_ko):
            return f"{m.last_name_ko} {m.first_name_ko}".strip()
        return m.full_name

    def get_competition_display(self, obj: Medal) -> str:
        if _req_lang(self) == "ko" and obj.competition_name_ko:
            return obj.competition_name_ko
        return obj.competition_name

    def get_location_display(self, obj: Medal) -> str:
        if _req_lang(self) == "ko" and obj.competition_location_ko:
            return obj.competition_location_ko
        return obj.competition_location


class PublicAchievementSerializer(serializers.ModelSerializer):
    """Exposes ONLY public achievement attributes — never certificates or admin notes."""

    class Meta:
        model = Achievement
        fields = [
            "id",
            "title",
            "title_ko",
            "description",
            "description_ko",
            "discipline",
            "achievement_date",
        ]


class PublicChampionListSerializer(serializers.ModelSerializer):
    """
    Public champion serializer — strictly omits email, phone, birth_date,
    admin_note, and unapproved submissions.
    """

    display_name = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    current_belt = serializers.SerializerMethodField()
    approved_medals_count = serializers.SerializerMethodField()

    class Meta:
        model = MemberProfile
        fields = [
            "slug",
            "display_name",
            "profile_photo",
            "primary_discipline",
            "bio",
            "current_belt",
            "approved_medals_count",
        ]

    def get_display_name(self, obj: MemberProfile) -> str:
        if _req_lang(self) == "ko" and (obj.last_name_ko or obj.first_name_ko):
            return f"{obj.last_name_ko} {obj.first_name_ko}".strip()
        return obj.full_name

    def get_bio(self, obj: MemberProfile) -> str:
        if _req_lang(self) == "ko":
            return obj.biography_ko or obj.biography
        return obj.biography or obj.biography_ko

    @extend_schema_field(BeltTypeSerializer(allow_null=True))
    def get_current_belt(self, obj: MemberProfile):
        belt = obj.current_approved_belt
        if not belt:
            return None
        return BeltTypeSerializer(belt.belt_type).data

    def get_approved_medals_count(self, obj: MemberProfile) -> int:
        annotated = getattr(obj, "approved_medal_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.medals.filter(approval_status=ApprovalStatus.APPROVED).count()


class PublicChampionDetailSerializer(PublicChampionListSerializer):
    medals = serializers.SerializerMethodField()
    achievements = serializers.SerializerMethodField()

    class Meta(PublicChampionListSerializer.Meta):
        fields = PublicChampionListSerializer.Meta.fields + ["medals", "achievements"]

    @extend_schema_field(PublicMedalSerializer(many=True))
    def get_medals(self, obj: MemberProfile):
        qs = obj.medals.filter(approval_status=ApprovalStatus.APPROVED).order_by("-award_date")
        return PublicMedalSerializer(qs, many=True, context=self.context).data

    @extend_schema_field(PublicAchievementSerializer(many=True))
    def get_achievements(self, obj: MemberProfile):
        qs = obj.achievements.filter(approval_status=ApprovalStatus.APPROVED).order_by(
            "-achievement_date"
        )
        return PublicAchievementSerializer(qs, many=True, context=self.context).data


class PublicContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "subject", "message", "language"]
        extra_kwargs = {"language": {"required": False}}

    def validate_message(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise serializers.ValidationError("Message must be at least 10 characters long.")
        return cleaned


# =============================================================================
# Authenticated Member Serializers (read-only moderation fields!)
# =============================================================================


class CurrentMemberProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    current_belt = serializers.SerializerMethodField()

    class Meta:
        model = MemberProfile
        fields = [
            "id",
            "email",
            "role",
            "membership_number",
            "joining_date",
            "membership_status",
            "admin_note",
            "first_name",
            "last_name",
            "first_name_ko",
            "last_name_ko",
            "profile_photo",
            "primary_discipline",
            "birth_date",
            "phone",
            "biography",
            "biography_ko",
            "public_profile_consent",
            "public_profile_visibility",
            "current_belt",
        ]
        read_only_fields = [
            "id",
            "email",
            "role",
            "membership_number",
            "joining_date",
            "membership_status",
            "admin_note",
            "current_belt",
        ]

    def validate(self, attrs):
        consent = attrs.get(
            "public_profile_consent",
            self.instance.public_profile_consent if self.instance else False,
        )
        visibility = attrs.get(
            "public_profile_visibility",
            self.instance.public_profile_visibility if self.instance else False,
        )
        if visibility and not consent:
            raise serializers.ValidationError(
                {
                    "public_profile_consent": (
                        "Public profile consent is required to enable public visibility."
                    )
                }
            )
        return attrs

    @extend_schema_field(BeltTypeSerializer(allow_null=True))
    def get_current_belt(self, obj: MemberProfile):
        belt = obj.current_approved_belt
        return BeltTypeSerializer(belt.belt_type).data if belt else None


class MemberAchievementSerializer(serializers.ModelSerializer):
    certificate_url = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = [
            "id",
            "title",
            "title_ko",
            "description",
            "description_ko",
            "discipline",
            "competition",
            "achievement_date",
            "certificate",
            "certificate_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "certificate_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"certificate": {"write_only": True, "required": False}}

    def get_certificate_url(self, obj: Achievement) -> str | None:
        return obj.get_certificate_url() or None


class MemberMedalSerializer(serializers.ModelSerializer):
    evidence_url = serializers.SerializerMethodField()

    class Meta:
        model = Medal
        fields = [
            "id",
            "medal_type",
            "discipline",
            "competition",
            "competition_name",
            "competition_name_ko",
            "competition_location",
            "competition_location_ko",
            "division_category",
            "award_date",
            "evidence",
            "evidence_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "evidence_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"evidence": {"write_only": True, "required": False}}

    def get_evidence_url(self, obj: Medal) -> str | None:
        return obj.get_evidence_url() or None


class MemberBeltHistorySerializer(serializers.ModelSerializer):
    belt_detail = BeltTypeSerializer(source="belt_type", read_only=True)
    certificate_url = serializers.SerializerMethodField()

    class Meta:
        model = BeltHistory
        fields = [
            "id",
            "belt_type",
            "belt_detail",
            "discipline",
            "award_date",
            "issuing_authority",
            "notes",
            "certificate",
            "certificate_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "belt_detail",
            "discipline",
            "certificate_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"certificate": {"write_only": True, "required": False}}

    def get_certificate_url(self, obj: BeltHistory) -> str | None:
        return obj.get_certificate_url() or None


class MemberActivitySerializer(serializers.ModelSerializer):
    photo_url = serializers.SerializerMethodField()

    class Meta:
        model = SocialActivity
        fields = [
            "id",
            "title",
            "title_ko",
            "description",
            "description_ko",
            "activity_date",
            "location",
            "location_ko",
            "photograph",
            "photo_url",
            "public_visibility_consent",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "photo_url",
            "approval_status",
            "admin_note",
            "correction_request",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {"photograph": {"write_only": True, "required": False}}

    def get_photo_url(self, obj: SocialActivity) -> str | None:
        return obj.get_private_photo_url() or None


class MemberNotificationSerializer(serializers.ModelSerializer):
    localized_message = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "localized_message",
            "notification_type",
            "target_url",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_localized_message(self, obj: Notification) -> str:
        if _req_lang(self) == "ko" and obj.message_ko:
            return obj.message_ko
        return obj.message


class CorrectionRequestAPISerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1500)


# =============================================================================
# Admin Moderation & Management Serializers
# =============================================================================


class AdminReviewDecisionSerializer(serializers.Serializer):
    approval_status = serializers.ChoiceField(
        choices=[
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.NEEDS_REVISION,
        ]
    )
    admin_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)

    def validate(self, attrs):
        st = attrs["approval_status"]
        note = (attrs.get("admin_note") or "").strip()
        if st in {ApprovalStatus.REJECTED, ApprovalStatus.NEEDS_REVISION} and not note:
            raise serializers.ValidationError(
                {"admin_note": "Administrator note is required for rejection or revision requests."}
            )
        return attrs


class AdminMembershipDecisionSerializer(serializers.Serializer):
    membership_status = serializers.ChoiceField(choices=MembershipStatus.choices)
    admin_note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class AdminMemberSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = MemberProfile
        fields = [
            "id",
            "membership_number",
            "slug",
            "email",
            "role",
            "is_active",
            "first_name",
            "last_name",
            "first_name_ko",
            "last_name_ko",
            "primary_discipline",
            "birth_date",
            "phone",
            "joining_date",
            "membership_status",
            "admin_note",
            "public_profile_consent",
            "public_profile_visibility",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "membership_number",
            "slug",
            "email",
            "role",
            "is_active",
            "membership_status",
            "reviewed_at",
            "created_at",
        ]


class AdminMedalModerationSerializer(MemberMedalSerializer):
    member_number = serializers.CharField(source="member.membership_number", read_only=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta(MemberMedalSerializer.Meta):
        extra_kwargs = {}
        fields = ["member", "member_number", "member_name"] + [
            f for f in MemberMedalSerializer.Meta.fields if f != "evidence"
        ]
        read_only_fields = fields


class AdminAchievementModerationSerializer(MemberAchievementSerializer):
    member_number = serializers.CharField(source="member.membership_number", read_only=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta(MemberAchievementSerializer.Meta):
        extra_kwargs = {}
        fields = ["member", "member_number", "member_name"] + [
            f for f in MemberAchievementSerializer.Meta.fields if f != "certificate"
        ]
        read_only_fields = fields


class AdminBeltModerationSerializer(MemberBeltHistorySerializer):
    member_number = serializers.CharField(source="member.membership_number", read_only=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta(MemberBeltHistorySerializer.Meta):
        extra_kwargs = {}
        fields = ["member", "member_number", "member_name"] + [
            f for f in MemberBeltHistorySerializer.Meta.fields if f != "certificate"
        ]
        read_only_fields = fields


class AdminActivityModerationSerializer(MemberActivitySerializer):
    member_number = serializers.CharField(source="member.membership_number", read_only=True)
    member_name = serializers.CharField(source="member.full_name", read_only=True)

    class Meta(MemberActivitySerializer.Meta):
        extra_kwargs = {}
        fields = ["member", "member_number", "member_name"] + [
            f for f in MemberActivitySerializer.Meta.fields if f != "photograph"
        ]
        read_only_fields = fields


class PostTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostTranslation
        fields = [
            "language",
            "title",
            "excerpt",
            "body",
            "featured_image_alt",
            "seo_title",
            "seo_description",
        ]


class AdminPostSerializer(serializers.ModelSerializer):
    translations = PostTranslationSerializer(many=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "slug",
            "category",
            "tags",
            "status",
            "published_at",
            "is_featured",
            "robots_index",
            "robots_follow",
            "translations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        translations_data = validated_data.pop("translations", [])
        tags = validated_data.pop("tags", [])
        post = Post.objects.create(**validated_data)
        if tags:
            post.tags.set(tags)
        for tr in translations_data:
            PostTranslation.objects.update_or_create(
                post=post, language=tr["language"], defaults=tr
            )
        return post

    def update(self, instance: Post, validated_data):
        translations_data = validated_data.pop("translations", None)
        tags = validated_data.pop("tags", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if translations_data is not None:
            for tr in translations_data:
                PostTranslation.objects.update_or_create(
                    post=instance, language=tr["language"], defaults=tr
                )
        return instance


class ProductTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTranslation
        fields = [
            "language",
            "name",
            "short_description",
            "description",
            "specifications",
            "seo_title",
            "seo_description",
        ]


class AdminProductSerializer(serializers.ModelSerializer):
    translations = ProductTranslationSerializer(many=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "slug",
            "sku",
            "category",
            "discipline",
            "price",
            "currency",
            "is_available",
            "is_featured",
            "status",
            "translations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        translations_data = validated_data.pop("translations", [])
        product = Product.objects.create(**validated_data)
        for tr in translations_data:
            ProductTranslation.objects.update_or_create(
                product=product, language=tr["language"], defaults=tr
            )
        return product

    def update(self, instance: Product, validated_data):
        translations_data = validated_data.pop("translations", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if translations_data is not None:
            for tr in translations_data:
                ProductTranslation.objects.update_or_create(
                    product=instance, language=tr["language"], defaults=tr
                )
        return instance


class PageTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageTranslation
        fields = ["language", "title", "subtitle", "summary", "body", "seo_title", "seo_description"]


class AdminPageSerializer(serializers.ModelSerializer):
    translations = PageTranslationSerializer(many=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "slug",
            "page_type",
            "status",
            "display_order",
            "show_in_footer",
            "translations",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        translations_data = validated_data.pop("translations", [])
        page = Page.objects.create(**validated_data)
        for tr in translations_data:
            PageTranslation.objects.update_or_create(
                page=page, language=tr["language"], defaults=tr
            )
        return page

    def update(self, instance: Page, validated_data):
        translations_data = validated_data.pop("translations", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if translations_data is not None:
            for tr in translations_data:
                PageTranslation.objects.update_or_create(
                    page=instance, language=tr["language"], defaults=tr
                )
        return instance


class PublicCompetitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = [
            "id",
            "slug",
            "discipline",
            "title_fa",
            "title_ko",
            "location_fa",
            "location_ko",
            "start_date",
            "end_date",
            "organizer",
            "organizer_ko",
        ]

"""Shared test helpers and realistic model/file factories for TECHWANDO tests."""
from __future__ import annotations

import datetime
import io
import shutil
import tempfile
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.accounts.models import User, UserRole
from apps.accounts.rbac import ensure_role_groups, sync_user_role_group
from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.belts.models import BeltHistory, BeltType
from apps.blog.models import Category, CategoryTranslation, Post, PostTranslation, Tag
from apps.competitions.models import Competition
from apps.core.models import ApprovalStatus, Discipline, LanguageChoice, PublicationStatus
from apps.medals.models import Medal, MedalType
from apps.members.models import MemberProfile, MembershipStatus
from apps.members.services import ensure_member_profile
from apps.pages.models import Page, PageTranslation, PageType
from apps.products.models import Product, ProductCategory, ProductCategoryTranslation, ProductTranslation

DEFAULT_PASSWORD = "Strong!Pass2026#Tw"


def make_png_upload(name: str = "evidence.png", color=(185, 28, 28)) -> SimpleUploadedFile:
    buf = io.BytesIO()
    img = Image.new("RGB", (120, 90), color=color)
    img.save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


def make_pdf_upload(name: str = "certificate.pdf") -> SimpleUploadedFile:
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"trailer << /Root 1 0 R /Size 4 >>\nstartxref\n180\n%%EOF\n"
    )
    return SimpleUploadedFile(name, pdf_bytes, content_type="application/pdf")


class TechwandoTestCase(TestCase):
    """Base test case using isolated temporary public and private media directories."""

    @classmethod
    def setUpClass(cls):
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="techwando_test_"))
        cls._media_root = cls._tmp_dir / "media"
        cls._private_root = cls._tmp_dir / "private_media"
        cls._media_root.mkdir(parents=True, exist_ok=True)
        cls._private_root.mkdir(parents=True, exist_ok=True)
        cls._override = override_settings(
            MEDIA_ROOT=cls._media_root,
            PRIVATE_MEDIA_ROOT=cls._private_root,
        )
        cls._override.enable()
        # Update private_media_storage location for tests
        from apps.core.storage import private_media_storage

        cls._orig_private_loc = private_media_storage._location
        private_media_storage._location = str(cls._private_root)
        private_media_storage.__dict__.pop("base_location", None)
        private_media_storage.__dict__.pop("location", None)
        super().setUpClass()
        ensure_role_groups()

    @classmethod
    def tearDownClass(cls):
        from apps.core.storage import private_media_storage

        super().tearDownClass()
        private_media_storage._location = cls._orig_private_loc
        private_media_storage.__dict__.pop("base_location", None)
        private_media_storage.__dict__.pop("location", None)
        cls._override.disable()
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)

    def create_user(
        self,
        email: str,
        *,
        role: str = UserRole.MEMBER,
        password: str = DEFAULT_PASSWORD,
        first_name: str = "آرش",
        last_name: str = "رضایی",
        preferred_language: str = LanguageChoice.PERSIAN,
        is_active: bool = True,
    ) -> User:
        if role == UserRole.SUPER_ADMIN:
            user = User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                preferred_language=preferred_language,
            )
            user.is_active = is_active
            user.save()
            return user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            preferred_language=preferred_language,
            is_active=is_active,
        )
        sync_user_role_group(user)
        return user

    def create_member(
        self,
        email: str,
        *,
        first_name: str = "کیان",
        last_name: str = "مرادی",
        first_name_ko: str = "キアン",
        last_name_ko: str = "モラディ",
        status: str = MembershipStatus.APPROVED,
        public: bool = True,
        discipline: str = Discipline.TAEKWONDO,
        phone: str = "+989121234567",
        birth_date: datetime.date = datetime.date(1998, 5, 14),
    ) -> tuple[User, MemberProfile]:
        user = self.create_user(
            email=email,
            role=UserRole.MEMBER,
            first_name=first_name,
            last_name=last_name,
        )
        profile = ensure_member_profile(user)
        profile.first_name = first_name
        profile.last_name = last_name
        profile.first_name_ko = first_name_ko
        profile.last_name_ko = last_name_ko
        profile.membership_status = status
        profile.public_profile_consent = public
        profile.public_profile_visibility = public
        profile.primary_discipline = discipline
        profile.phone = phone
        profile.birth_date = birth_date
        profile.biography = "قهرمان ملی تکواندو"
        profile.biography_ko = "テコンドー全国챔피언"
        profile.save()
        return user, profile

    def create_belt_type(
        self,
        code: str = "DAN-1",
        order: int = 10,
        discipline: str = Discipline.TAEKWONDO,
        is_black: bool = True,
    ) -> BeltType:
        belt, _ = BeltType.objects.get_or_create(
            discipline=discipline,
            rank_code=code,
            defaults={
                "rank_order": order,
                "name_fa": "کمربند مشکی دان ۱" if is_black else "کمربند آبی",
                "name_ko": "黒帯 初段" if is_black else "青帯",
                "color_hex": "#111827" if is_black else "#1D4ED8",
                "is_black_belt": is_black,
            },
        )
        return belt

    def create_competition(
        self,
        slug: str = "asia-open-2026",
        discipline: str = Discipline.TAEKWONDO,
    ) -> Competition:
        comp, _ = Competition.objects.get_or_create(
            slug=slug,
            defaults={
                "title_fa": "مسابقات آزاد آسیا ۲۰۲۶",
                "title_ko": "アジアオープン選手権 2026",
                "location_fa": "توکیو، ژاپن",
                "location_ko": "日本・東京",
                "organizer": "فدراسیون آسیا",
                "organizer_ko": "アジア連盟",
                "discipline": discipline,
                "start_date": datetime.date(2026, 5, 10),
                "end_date": datetime.date(2026, 5, 12),
                "is_published": True,
            },
        )
        return comp

    def create_bilingual_post(
        self,
        slug: str = "poomsae-mastery",
        status: str = PublicationStatus.PUBLISHED,
        published_at=None,
        include_ko: bool = True,
    ) -> Post:
        from django.utils import timezone

        cat, _ = Category.objects.get_or_create(slug="technical")
        CategoryTranslation.objects.get_or_create(
            category=cat, language="fa", defaults={"name": "آموزش فنی"}
        )
        CategoryTranslation.objects.get_or_create(
            category=cat, language="ko", defaults={"name": "技術解説"}
        )
        tag, _ = Tag.objects.get_or_create(
            slug="black-belt",
            defaults={"name_fa": "کمربند مشکی", "name_ko": "黒帯"},
        )
        post = Post.objects.create(
            slug=slug,
            category=cat,
            status=status,
            published_at=published_at or (timezone.now() - datetime.timedelta(days=1)),
            is_featured=True,
        )
        post.tags.add(tag)
        PostTranslation.objects.create(
            post=post,
            language="fa",
            title="اصول پومسه پیشرفته",
            excerpt="راهنمای جامع تعادل و تنفس در پومسه.",
            body="متن کامل مقاله آموزشی پومسه به زبان فارسی.",
            seo_title="آموزش پومسه | تکواندو",
            seo_description="توضیحات سئو پومسه فارسی.",
        )
        if include_ko:
            PostTranslation.objects.create(
                post=post,
                language="ko",
                title="고급 품새의 핵심",
                excerpt="呼吸と重心の精密なコントロール解説。",
                body="日本語による上級プムセの解説本文です。",
                seo_title="プムセ技術解説 | TECHWANDO",
                seo_description="日本語のSEOディスクリプション。",
            )
        return post

    def create_bilingual_product(
        self,
        slug: str = "pro-dobok",
        sku: str = "TW-TEST-01",
        price="12500",
    ) -> Product:
        cat, _ = ProductCategory.objects.get_or_create(slug="uniforms")
        ProductCategoryTranslation.objects.get_or_create(
            category=cat, language="fa", defaults={"name": "لباس رزمی"}
        )
        ProductCategoryTranslation.objects.get_or_create(
            category=cat, language="ko", defaults={"name": "公式道着"}
        )
        product = Product.objects.create(
            slug=slug,
            sku=sku,
            category=cat,
            discipline=Discipline.TAEKWONDO,
            price=price,
            currency="JPY",
            is_available=True,
            is_featured=True,
            status=PublicationStatus.PUBLISHED,
        )
        ProductTranslation.objects.create(
            product=product,
            language="fa",
            name="لباس دوبوک قهرمانی",
            short_description="دوبوک استاندارد مسابقاتی",
            description="پارچه تنفس‌پذیر مناسب مسابقات رسمی.",
            specifications="وزن: ۲۱۰ گرم",
        )
        ProductTranslation.objects.create(
            product=product,
            language="ko",
            name="公認競技用ドボク",
            short_description="公式大会対応モデル",
            description="通気性に優れた高品質な競技用道着です。",
            specifications="重量: 210g/m2",
        )
        return product

    def create_bilingual_page(
        self,
        slug: str = "about",
        page_type: str = PageType.ABOUT,
    ) -> Page:
        page = Page.objects.create(
            slug=slug,
            page_type=page_type,
            status=PublicationStatus.PUBLISHED,
        )
        PageTranslation.objects.create(
            page=page,
            language="fa",
            title="درباره آکادمی تکواندو",
            subtitle="میراث رزمی و آموزش علمی",
            summary="خلاصه معرفی باشگاه تکواندو.",
            body="متن کامل معرفی آکادمی تکواندو به زبان فارسی.",
        )
        PageTranslation.objects.create(
            page=page,
            language="ko",
            title="TECHWANDOアカデミー紹介",
            subtitle="武道の伝統と現代スポーツ科学",
            summary="TECHWANDOクラブの概要。",
            body="TECHWANDOアカデミーの詳細な日本語紹介文です。",
        )
        return page

"""Tests for the public gallery page and hero banner (consent-gated photos only)."""
from __future__ import annotations

import datetime

from django.urls import reverse

from apps.activities.models import SocialActivity
from apps.core.models import ApprovalStatus
from tests.base import TechwandoTestCase, make_png_upload


class GallerySmokeTests(TechwandoTestCase):
    def setUp(self):
        super().setUp()
        _, self.member = self.create_member("gallery@tw.test", public=True)
        _, self.private_member = self.create_member("nogallery@tw.test", public=False)

    def test_home_page_has_banner_fa_and_ko(self):
        for lang in ("fa", "ko"):
            resp = self.client.get(f"/{lang}/")
            self.assertEqual(resp.status_code, 200, f"home {lang}")
            content = resp.content.decode("utf-8")
            self.assertIn("hero-banner.png", content, f"banner missing in {lang}")
            self.assertIn("hero-banner", content, f"banner class missing in {lang}")

    def test_gallery_empty_state(self):
        for lang in ("fa", "ko"):
            resp = self.client.get(f"/{lang}/gallery/")
            self.assertEqual(resp.status_code, 200, f"gallery {lang}")
            content = resp.content.decode("utf-8")
            # Empty state: no gallery grid rendered
            self.assertNotIn("gallery-grid", content, f"grid should be empty in {lang}")
            # Exactly one h1
            self.assertEqual(content.count("<h1"), 1, f"h1 count in {lang}")
            self.assertIn("نگارخانه باشگاه" if lang == "fa" else "클럽 갤러리", content)
            self.assertIn('hreflang="fa-IR"', content)
            self.assertIn('hreflang="ko-KR"', content)
            self.assertIn('dir="rtl"' if lang == "fa" else 'dir="ltr"', content)

    def test_gallery_shows_only_consented_photos(self):
        public_photo = SocialActivity.objects.create(
            member=self.member,
            title="تمرین مشترک باشگاه",
            title_ko="클럽 합동 훈련",
            description="تمرین مشترک",
            activity_date=datetime.date(2026, 4, 1),
            location="تهران",
            location_ko="테헤란",
            public_visibility_consent=True,
            approval_status=ApprovalStatus.APPROVED,
            photograph=make_png_upload("club.png"),
        )
        # Non-consented approved activity must NOT appear
        SocialActivity.objects.create(
            member=self.member,
            title="فعالیت بدون رضایت",
            description="خصوصی",
            activity_date=datetime.date(2026, 4, 2),
            location="تهران",
            public_visibility_consent=False,
            approval_status=ApprovalStatus.APPROVED,
            photograph=make_png_upload("secret.png"),
        )
        # Consented but no photo must NOT appear
        SocialActivity.objects.create(
            member=self.member,
            title="فعالیت بدون عکس",
            description="بدون عکس",
            activity_date=datetime.date(2026, 4, 3),
            location="تهران",
            public_visibility_consent=True,
            approval_status=ApprovalStatus.APPROVED,
        )
        # Private member's photo must NOT appear
        SocialActivity.objects.create(
            member=self.private_member,
            title="عکس عضو خصوصی",
            description="خصوصی",
            activity_date=datetime.date(2026, 4, 4),
            location="تهران",
            public_visibility_consent=True,
            approval_status=ApprovalStatus.APPROVED,
            photograph=make_png_upload("private.png"),
        )

        SocialActivity.objects.create(
            member=self.member,
            title="عکس در انتظار تأیید",
            description="در انتظار",
            activity_date=datetime.date(2026, 4, 5),
            location="تهران",
            public_visibility_consent=True,
            approval_status=ApprovalStatus.PENDING,
            photograph=make_png_upload("pending.png"),
        )

        resp = self.client.get("/fa/gallery/")
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode("utf-8")
        self.assertIn("تمرین مشترک باشگاه", content)
        self.assertIn("gallery-card", content)
        self.assertNotIn("فعالیت بدون رضایت", content)
        self.assertNotIn("فعالیت بدون عکس", content)
        self.assertNotIn("عکس عضو خصوصی", content)
        self.assertNotIn("عکس در انتظار تأیید", content)
        self.assertIn(public_photo.get_photo_url(), content)
        self.assertEqual(self.client.get(public_photo.get_photo_url()).status_code, 200)
        self.assertEqual(content.count("<h1"), 1)

        resp_ko = self.client.get("/ko/gallery/")
        self.assertEqual(resp_ko.status_code, 200)
        content_ko = resp_ko.content.decode("utf-8")
        self.assertIn("클럽 합동 훈련", content_ko)
        self.assertEqual(content_ko.count("<h1"), 1)

        public_photo.public_visibility_consent = False
        public_photo.save(update_fields=["public_visibility_consent"])
        self.assertNotContains(self.client.get("/fa/gallery/"), "تمرین مشترک باشگاه")
        self.assertEqual(self.client.get(public_photo.get_photo_url()).status_code, 404)

    def test_gallery_search(self):
        SocialActivity.objects.create(
            member=self.member,
            title="مسابقات قهرمانی",
            description="مسابقات",
            activity_date=datetime.date(2026, 5, 1),
            location="اصفهان",
            public_visibility_consent=True,
            approval_status=ApprovalStatus.APPROVED,
            photograph=make_png_upload("comp.png"),
        )
        resp = self.client.get("/fa/gallery/?q=مسابقات")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("مسابقات قهرمانی", resp.content.decode("utf-8"))

        resp = self.client.get("/fa/gallery/?q=ناموجودxyz")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("مسابقات قهرمانی", resp.content.decode("utf-8"))

    def test_gallery_pagination_preserves_search(self):
        for i in range(13):
            SocialActivity.objects.create(
                member=self.member,
                title=f"Training {i}",
                description="Practice",
                activity_date=datetime.date(2025, 4, 1),
                location="Tehran",
                public_visibility_consent=True,
                approval_status=ApprovalStatus.APPROVED,
                photograph=make_png_upload(f"training{i}.png"),
            )
        response = self.client.get("/fa/gallery/", {"q": "Training"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["photos"]), 12)
        self.assertEqual(response.context["photo_count"], 13)
        self.assertContains(response, "q=Training&amp;page=2")
        response = self.client.get("/fa/gallery/", {"q": "Training", "page": 2})
        self.assertEqual(len(response.context["photos"]), 1)

    def test_gallery_route_reverses(self):
        from django.utils import translation

        with translation.override("fa"):
            self.assertEqual(reverse("pages:gallery"), "/fa/gallery/")
        with translation.override("ko"):
            self.assertEqual(reverse("pages:gallery"), "/ko/gallery/")

"""Comprehensive REST API (/api/v1/) tests: public, member, admin, CSRF, i18n, and OpenAPI."""
import datetime

from django.core import cache
from rest_framework.test import APIClient

from apps.accounts.models import UserRole
from apps.core.models import ApprovalStatus, Discipline
from apps.medals.models import Medal, MedalType
from apps.members.models import MembershipStatus
from apps.pages.models import PageType
from apps.notifications.models import Notification
from tests.base import TeakwondoTestCase


class RestAPITests(TeakwondoTestCase):
    def setUp(self):
        cache.cache.clear()
        self.api = APIClient()
        self.super_admin = self.create_user("api_super@tw.test", role=UserRole.SUPER_ADMIN)
        self.moderator = self.create_user("api_mod@tw.test", role=UserRole.MODERATOR)
        self.content_admin = self.create_user("api_content@tw.test", role=UserRole.CONTENT_ADMIN)
        self.user_a, self.member_a = self.create_member(
            "api_a@tw.test", first_name="سامان", last_name="کاظمی", public=True
        )
        self.user_b, self.member_b = self.create_member(
            "api_b@tw.test", first_name="کنتا", last_name="ساتو", public=True
        )

        self.belt = self.create_belt_type()
        self.comp = self.create_competition()
        self.post = self.create_bilingual_post("api-post")
        self.product = self.create_bilingual_product("api-dobok", "TW-API-01")
        self.page = self.create_bilingual_page("about", PageType.ABOUT)

        self.approved_medal = Medal.objects.create(
            member=self.member_a,
            medal_type=MedalType.GOLD,
            discipline=Discipline.TAEKWONDO,
            competition=self.comp,
            competition_name="مسابقات آسیایی",
            competition_name_ko="アジア大会",
            award_date=datetime.date(2026, 5, 11),
            approval_status=ApprovalStatus.APPROVED,
        )
        self.pending_b_medal = Medal.objects.create(
            member=self.member_b,
            medal_type=MedalType.SILVER,
            discipline=Discipline.KARATE,
            competition_name="جام توکیو",
            award_date=datetime.date(2026, 6, 1),
            approval_status=ApprovalStatus.PENDING,
        )

    def test_public_endpoints_and_openapi_schema_with_localization(self):
        # Blog in Persian vs Korean
        fa_posts = self.api.get("/api/v1/public/blog/", HTTP_ACCEPT_LANGUAGE="fa")
        ko_posts = self.api.get("/api/v1/public/blog/", HTTP_ACCEPT_LANGUAGE="ko")
        self.assertEqual(fa_posts.status_code, 200)
        self.assertIn("count", fa_posts.data)
        self.assertEqual(fa_posts.data["results"][0]["title"], "اصول پومسه پیشرفته")
        self.assertEqual(ko_posts.data["results"][0]["title"], "고급 품새의 핵심")

        # Products, Pages, Champions, Medal Winners (only APPROVED medals; no private fields)
        self.assertEqual(self.api.get("/api/v1/public/products/").status_code, 200)
        self.assertEqual(self.api.get("/api/v1/public/pages/about/").status_code, 200)

        champs = self.api.get(f"/api/v1/public/champions/{self.member_a.slug}/")
        self.assertEqual(champs.status_code, 200)
        self.assertNotIn("email", champs.data)
        self.assertNotIn("phone", champs.data)
        self.assertNotIn("birth_date", champs.data)

        medals = self.api.get("/api/v1/public/medals/")
        self.assertEqual(medals.status_code, 200)
        self.assertEqual(medals.data["count"], 1)  # Pending medal excluded!

        # Public Contact POST
        contact = self.api.post(
            "/api/v1/public/contact/",
            {
                "name": "API Visitor",
                "email": "visitor@example.com",
                "subject": "Membership Info",
                "message": "I would like to join the evening Taekwondo class.",
                "language": "fa",
            },
            format="json",
        )
        self.assertEqual(contact.status_code, 201)

        # OpenAPI schema & Swagger UI
        self.assertEqual(self.api.get("/api/v1/schema/").status_code, 200)
        self.assertEqual(self.api.get("/api/v1/docs/").status_code, 200)

    def test_csrf_enforced_on_session_authenticated_api_writes(self):
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_login(self.user_a)
        # Missing CSRF token on session-authenticated write MUST be rejected with 403
        res = csrf_client.post(
            "/api/v1/member/achievements/",
            {
                "title": "No CSRF",
                "discipline": "TAEKWONDO",
                "achievement_date": "2026-04-01",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 403)
        self.assertIn("error", res.data)  # Consistent error envelope

    def test_member_api_isolation_tamper_resistance_and_workflow(self):
        # Unauthenticated blocked
        self.assertIn(self.api.get("/api/v1/member/profile/").status_code, (401, 403))
        self.assertIn(self.api.get("/api/v1/admin/members/").status_code, (401, 403))

        # Authenticate as Member A
        self.api.force_authenticate(user=self.user_a)
        prof = self.api.get("/api/v1/member/profile/")
        self.assertEqual(prof.status_code, 200)
        self.assertEqual(prof.data["membership_number"], self.member_a.membership_number)

        # Member A submits achievement attempting to self-approve & spoof member_b
        created = self.api.post(
            "/api/v1/member/achievements/",
            {
                "title": "قهرمان استان",
                "discipline": "TAEKWONDO",
                "achievement_date": "2026-05-01",
                "approval_status": "APPROVED",
                "admin_note": "Hacked",
                "member": self.member_b.pk,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data["approval_status"], ApprovalStatus.PENDING)
        self.assertEqual(created.data["admin_note"], "")

        # Member A cannot see or touch Member B's medal
        self.assertEqual(
            self.api.get(f"/api/v1/member/medals/{self.pending_b_medal.pk}/").status_code, 404
        )
        # Member A cannot delete their own APPROVED medal, but CAN request correction
        self.assertEqual(
            self.api.delete(f"/api/v1/member/medals/{self.approved_medal.pk}/").status_code, 403
        )
        corr = self.api.post(
            f"/api/v1/member/medals/{self.approved_medal.pk}/request_correction/",
            {"reason": "درخواست اصلاح عنوان رویداد قهرمانی در سیستم."},
            format="json",
        )
        self.assertEqual(corr.status_code, 200)
        self.assertEqual(corr.data["approval_status"], ApprovalStatus.NEEDS_REVISION)

        # Member A blocked from admin API endpoints
        self.assertEqual(self.api.get("/api/v1/admin/members/").status_code, 403)
        self.assertEqual(self.api.get("/api/v1/admin/medals/").status_code, 403)
        self.assertEqual(self.api.get("/api/v1/admin/posts/").status_code, 403)

    def test_admin_api_moderation_member_approval_and_bilingual_content(self):
        # Moderator approves Member B's pending medal via API
        self.api.force_authenticate(user=self.moderator)
        res = self.api.post(
            f"/api/v1/admin/medals/{self.pending_b_medal.pk}/review/",
            {"approval_status": ApprovalStatus.APPROVED, "admin_note": "گواهی تایید شد."},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.pending_b_medal.refresh_from_db()
        self.assertEqual(self.pending_b_medal.approval_status, ApprovalStatus.APPROVED)
        self.assertTrue(Notification.objects.filter(recipient=self.user_b).exists())

        # Moderator cannot manage blog posts (403), Content Admin CAN
        self.assertEqual(self.api.get("/api/v1/admin/posts/").status_code, 403)

        self.api.force_authenticate(user=self.content_admin)
        create_post = self.api.post(
            "/api/v1/admin/posts/",
            {
                "slug": "new-bilingual-article",
                "status": "PUBLISHED",
                "translations": [
                    {"language": "fa", "title": "مقاله جدید", "body": "متن فارسی مقاله."},
                    {"language": "ko", "title": "新着記事", "body": "日本語の記事本文。"},
                ],
            },
            format="json",
        )
        self.assertEqual(create_post.status_code, 201)

        # Super Admin approves a pending membership application via API
        _, applicant = self.create_member("pending_api@tw.test", status=MembershipStatus.PENDING)
        self.api.force_authenticate(user=self.super_admin)
        app_res = self.api.post(
            f"/api/v1/admin/members/{applicant.pk}/review/",
            {"membership_status": MembershipStatus.APPROVED, "admin_note": "Approved via Admin API"},
            format="json",
        )
        self.assertEqual(app_res.status_code, 200)
        applicant.refresh_from_db()
        self.assertEqual(applicant.membership_status, MembershipStatus.APPROVED)

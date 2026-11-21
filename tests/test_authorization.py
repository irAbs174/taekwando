"""RBAC and object-level isolation tests across Member Portal and Admin Panel."""
import datetime

from apps.accounts.models import UserRole
from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.belts.models import BeltHistory
from apps.competitions.models import CompetitionParticipation
from apps.core.models import ApprovalStatus, Discipline
from apps.medals.models import Medal, MedalType
from apps.notifications.models import Notification
from tests.base import TechwandoTestCase


class AuthorizationAndIsolationTests(TechwandoTestCase):
    def setUp(self):
        self.super_admin = self.create_user("super@tw.test", role=UserRole.SUPER_ADMIN)
        self.content_admin = self.create_user("content@tw.test", role=UserRole.CONTENT_ADMIN)
        self.club_manager = self.create_user("manager@tw.test", role=UserRole.CLUB_MANAGER)
        self.moderator = self.create_user("moderator@tw.test", role=UserRole.MODERATOR)

        self.user_a, self.member_a = self.create_member("member_a@tw.test", first_name="علی")
        self.user_b, self.member_b = self.create_member("member_b@tw.test", first_name="رضا")

        self.belt = self.create_belt_type()
        self.comp = self.create_competition()

        self.b_ach = Achievement.objects.create(
            member=self.member_b,
            title="قهرمانی کشور",
            discipline=Discipline.TAEKWONDO,
            achievement_date=datetime.date(2026, 2, 1),
        )
        self.b_medal = Medal.objects.create(
            member=self.member_b,
            medal_type=MedalType.GOLD,
            discipline=Discipline.TAEKWONDO,
            competition_name="جام ملی",
            award_date=datetime.date(2026, 3, 1),
        )
        self.b_belt = BeltHistory.objects.create(
            member=self.member_b,
            belt_type=self.belt,
            discipline=Discipline.TAEKWONDO,
            award_date=datetime.date(2026, 1, 15),
        )
        self.b_part = CompetitionParticipation.objects.create(
            member=self.member_b,
            competition=self.comp,
            division_category="-68kg",
        )
        self.b_act = SocialActivity.objects.create(
            member=self.member_b,
            title="کارگاه آموزشی نوجوانان",
            description="برگزاری تمرین رایگان برای دانش‌آموزان.",
            activity_date=datetime.date(2026, 4, 1),
            location="تهران",
        )
        self.b_notif = Notification.objects.create(
            recipient=self.user_b,
            message="پیام خصوصی",
            message_ko="個別通知",
        )

    def test_unauthenticated_redirected_from_member_and_admin_portals(self):
        protected_urls = [
            "/fa/member/dashboard/",
            "/fa/member/profile/",
            "/fa/member/achievements/",
            "/fa/member/medals/",
            "/fa/member/belts/",
            "/fa/member/competitions/",
            "/fa/member/activities/",
            "/fa/member/notifications/",
            "/fa/accounts/management/",
            "/fa/accounts/management/moderation/",
            "/fa/accounts/management/members/",
            "/fa/blog/manage/",
            "/fa/products/manage/",
            "/fa/pages/manage/",
            "/fa/management/seo/",
            "/fa/contact/manage/",
            "/fa/management/audit-logs/",
        ]
        for url in protected_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 302, f"Expected redirect for {url}")
            self.assertIn("/accounts/login/", resp["Location"])

    def test_member_a_cannot_view_edit_or_delete_member_b_records(self):
        self.client.force_login(self.user_a)
        forbidden_or_not_found = [
            f"/fa/member/achievements/{self.b_ach.pk}/",
            f"/fa/member/achievements/{self.b_ach.pk}/edit/",
            f"/fa/member/achievements/{self.b_ach.pk}/delete/",
            f"/fa/member/medals/{self.b_medal.pk}/",
            f"/fa/member/medals/{self.b_medal.pk}/edit/",
            f"/fa/member/medals/{self.b_medal.pk}/delete/",
            f"/fa/member/belts/{self.b_belt.pk}/",
            f"/fa/member/belts/{self.b_belt.pk}/edit/",
            f"/fa/member/competitions/{self.b_part.pk}/",
            f"/fa/member/competitions/{self.b_part.pk}/edit/",
            f"/fa/member/activities/{self.b_act.pk}/",
            f"/fa/member/activities/{self.b_act.pk}/edit/",
        ]
        for url in forbidden_or_not_found:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 404, f"Member A must not access {url}")

        # Member A cannot mark Member B's notification read
        notif_resp = self.client.post(f"/fa/member/notifications/{self.b_notif.pk}/read/")
        self.assertEqual(notif_resp.status_code, 404)
        self.b_notif.refresh_from_db()
        self.assertFalse(self.b_notif.is_read)

        # Member A's list pages do not contain Member B's records
        list_resp = self.client.get("/fa/member/achievements/")
        self.assertEqual(list_resp.status_code, 200)
        self.assertNotContains(list_resp, "قهرمانی کشور")

    def test_regular_member_forbidden_from_all_admin_views_and_django_admin(self):
        self.client.force_login(self.user_a)
        admin_urls = [
            "/fa/accounts/management/",
            "/fa/accounts/management/moderation/",
            "/fa/accounts/management/members/",
            "/fa/blog/manage/",
            "/fa/products/manage/",
            "/fa/pages/manage/",
            "/fa/management/seo/",
            "/fa/contact/manage/",
            "/fa/management/audit-logs/",
            "/fa/member/belts/admin-types/",
            "/fa/member/competitions/manage/",
        ]
        for url in admin_urls:
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 403, f"Member must get 403 on {url}")

        # Regular member is not is_staff, so Django Admin redirects to staff login
        dj_admin = self.client.get("/django-admin/")
        self.assertEqual(dj_admin.status_code, 302)

    def test_role_boundaries_across_admin_roles(self):
        # CONTENT_ADMIN can manage blog/products/pages/seo/contact, NOT member approvals or moderation
        self.client.force_login(self.content_admin)
        self.assertEqual(self.client.get("/fa/accounts/management/").status_code, 200)
        self.assertEqual(self.client.get("/fa/blog/manage/").status_code, 200)
        self.assertEqual(self.client.get("/fa/products/manage/").status_code, 200)
        self.assertEqual(self.client.get("/fa/pages/manage/").status_code, 200)
        self.assertEqual(self.client.get("/fa/management/seo/").status_code, 200)
        self.assertEqual(self.client.get("/fa/contact/manage/").status_code, 200)
        self.assertEqual(self.client.get("/fa/accounts/management/members/").status_code, 403)
        self.assertEqual(self.client.get("/fa/accounts/management/moderation/").status_code, 403)
        self.assertEqual(self.client.get("/fa/management/audit-logs/").status_code, 403)

        # MODERATOR can review moderation queue, NOT manage blog/products/members/roles
        self.client.force_login(self.moderator)
        self.assertEqual(self.client.get("/fa/accounts/management/moderation/").status_code, 200)
        self.assertEqual(self.client.get("/fa/blog/manage/").status_code, 403)
        self.assertEqual(self.client.get("/fa/accounts/management/members/").status_code, 403)

        # CLUB_MANAGER can manage members, moderation, belts, competitions, audit logs, NOT change roles to SUPER_ADMIN
        self.client.force_login(self.club_manager)
        self.assertEqual(self.client.get("/fa/accounts/management/members/").status_code, 200)
        self.assertEqual(self.client.get("/fa/accounts/management/moderation/").status_code, 200)
        self.assertEqual(self.client.get("/fa/management/audit-logs/").status_code, 200)
        self.assertEqual(self.client.get("/fa/blog/manage/").status_code, 403)

        # Club manager attempting POST action=change_role must NOT escalate member to SUPER_ADMIN
        self.client.post(
            f"/fa/accounts/management/members/{self.member_a.pk}/",
            {"action": "change_role", "role": UserRole.SUPER_ADMIN},
        )
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.role, UserRole.MEMBER)

        # SUPER_ADMIN can access everything and assign roles
        self.client.force_login(self.super_admin)
        for url in [
            "/fa/accounts/management/",
            "/fa/accounts/management/members/",
            "/fa/accounts/management/moderation/",
            "/fa/blog/manage/",
            "/fa/products/manage/",
            "/fa/pages/manage/",
            "/fa/management/seo/",
            "/fa/contact/manage/",
            "/fa/management/audit-logs/",
            "/django-admin/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, f"SuperAdmin failed on {url}")

        self.client.post(
            f"/fa/accounts/management/members/{self.member_a.pk}/",
            {"action": "change_role", "role": UserRole.MODERATOR},
        )
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.role, UserRole.MODERATOR)

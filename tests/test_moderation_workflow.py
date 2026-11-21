"""Approval and moderation workflow tests across medals, belts, achievements, activities, and memberships."""
import datetime

from django.core.exceptions import PermissionDenied

from apps.accounts.models import UserRole
from apps.audit_logs.models import AuditLog
from apps.core.models import ApprovalStatus, Discipline, ReviewLog
from apps.core.services import ModerationService
from apps.medals.models import Medal, MedalType
from apps.members.models import MembershipStatus
from apps.members.services import ensure_member_profile
from apps.notifications.models import Notification
from tests.base import TeakwondoTestCase, make_pdf_upload


class ModerationWorkflowTests(TeakwondoTestCase):
    def setUp(self):
        self.moderator = self.create_user("mod@tw.test", role=UserRole.MODERATOR)
        self.manager = self.create_user("mgr@tw.test", role=UserRole.CLUB_MANAGER)
        self.member_user, self.member = self.create_member(
            "champ@tw.test", first_name="نیما", last_name="هدایتی", public=True
        )
        self.other_user, self.other_member = self.create_member(
            "other@tw.test", first_name="بهرام", last_name="صادقی"
        )
        self.comp = self.create_competition()
        self.belt = self.create_belt_type()

    def test_member_medal_submission_full_lifecycle(self):
        # 1. Member submits medal (trying to tamper status + member_id)
        self.client.force_login(self.member_user)
        resp = self.client.post(
            "/fa/member/medals/add/",
            {
                "medal_type": MedalType.GOLD,
                "discipline": Discipline.TAEKWONDO,
                "competition": self.comp.pk,
                "competition_name": "مسابقات آزاد آسیا ۲۰۲۶",
                "competition_name_ko": "アジアオープン 2026",
                "competition_location": "توکیو",
                "competition_location_ko": "東京",
                "division_category": "کیوروگی -۶۸ کیلوگرم",
                "award_date": "2026-05-11",
                "evidence": make_pdf_upload("gold_cert.pdf"),
                # Tampered fields must be ignored!
                "approval_status": ApprovalStatus.APPROVED,
                "admin_note": "Self approved",
                "member": self.other_member.pk,
            },
        )
        self.assertEqual(resp.status_code, 302)
        medal = Medal.objects.get(member=self.member)
        self.assertEqual(medal.approval_status, ApprovalStatus.PENDING)
        self.assertEqual(medal.admin_note, "")
        self.assertEqual(medal.member_id, self.member.pk)

        # Moderator was notified of new submission
        self.assertTrue(Notification.objects.filter(recipient=self.moderator).exists())

        # 2. PENDING medal MUST NOT appear on public Medal Winners page
        pub_resp = self.client.get("/fa/champions/medals/")
        self.assertNotContains(pub_resp, "کیوروگی -۶۸ کیلوگرم")

        # 3. Moderator requests revision (requires note)
        self.client.force_login(self.moderator)
        rev_resp = self.client.post(
            f"/fa/accounts/management/moderation/medal/{medal.pk}/",
            {
                "approval_status": ApprovalStatus.NEEDS_REVISION,
                "admin_note": "لطفاً شماره حکم قهرمانی را در توضیحات اضافه کنید.",
            },
        )
        self.assertEqual(rev_resp.status_code, 302)
        medal.refresh_from_db()
        self.assertEqual(medal.approval_status, ApprovalStatus.NEEDS_REVISION)
        self.assertIn("شماره حکم", medal.admin_note)
        self.assertTrue(Notification.objects.filter(recipient=self.member_user).exists())

        # 4. Member edits & resubmits -> status returns to PENDING
        self.client.force_login(self.member_user)
        resub = self.client.post(
            f"/fa/member/medals/{medal.pk}/edit/",
            {
                "medal_type": MedalType.GOLD,
                "discipline": Discipline.TAEKWONDO,
                "competition": self.comp.pk,
                "competition_name": "مسابقات آزاد آسیا ۲۰۲۶",
                "competition_name_ko": "アジアオープン 2026",
                "competition_location": "توکیو",
                "competition_location_ko": "東京",
                "division_category": "کیوروگی -۶۸ کیلوگرم",
                "award_date": "2026-05-11",
                "notes": "شماره حکم فدراسیون: AS-9921",
            },
        )
        self.assertEqual(resub.status_code, 302)
        medal.refresh_from_db()
        self.assertEqual(medal.approval_status, ApprovalStatus.PENDING)

        # 5. Moderator approves medal -> ReviewLog + AuditLog + Member Notification + Public visibility
        self.client.force_login(self.moderator)
        app_resp = self.client.post(
            f"/fa/accounts/management/moderation/medal/{medal.pk}/",
            {
                "approval_status": ApprovalStatus.APPROVED,
                "admin_note": "حکم فدراسیون بررسی و تایید شد.",
            },
        )
        self.assertEqual(app_resp.status_code, 302)
        medal.refresh_from_db()
        self.assertEqual(medal.approval_status, ApprovalStatus.APPROVED)
        self.assertEqual(medal.reviewer, self.moderator)
        self.assertIsNotNone(medal.reviewed_at)

        # Now visible on public Medal Winners page (both Persian and Korean!)
        self.assertContains(self.client.get("/fa/champions/medals/"), "نیما هدایتی")
        self.assertContains(self.client.get("/ko/champions/medals/"), "アジアオープン選手権 2026")

        # 6. Approved record CANNOT be directly edited or deleted by member
        self.client.force_login(self.member_user)
        self.assertEqual(self.client.get(f"/fa/member/medals/{medal.pk}/edit/").status_code, 403)
        self.assertEqual(self.client.post(f"/fa/member/medals/{medal.pk}/delete/").status_code, 403)

        # 7. Member CAN submit a formal correction request -> NEEDS_REVISION (withdrawn from public until re-approved)
        corr_resp = self.client.post(
            f"/fa/member/medals/{medal.pk}/request-correction/",
            {"reason": "تصحیح رده وزنی از منفی ۶۸ به منفی ۷۴ کیلوگرم بر اساس حکم اصلاحی."},
        )
        self.assertEqual(corr_resp.status_code, 302)
        medal.refresh_from_db()
        self.assertEqual(medal.approval_status, ApprovalStatus.NEEDS_REVISION)
        self.assertGreaterEqual(ReviewLog.objects.count(), 4)
        self.assertTrue(AuditLog.objects.filter(action="SUBMISSION_APPROVED").exists())

    def test_self_approval_is_strictly_forbidden(self):
        mod_profile = ensure_member_profile(self.moderator)
        own_medal = Medal.objects.create(
            member=mod_profile,
            medal_type=MedalType.SILVER,
            discipline=Discipline.KARATE,
            competition_name="مسابقه داخلی",
            award_date=datetime.date(2026, 4, 1),
        )
        with self.assertRaises(PermissionDenied):
            ModerationService.review_submission(
                own_medal,
                reviewer=self.moderator,
                new_status=ApprovalStatus.APPROVED,
                note="Trying to approve my own medal",
            )
        own_medal.refresh_from_db()
        self.assertEqual(own_medal.approval_status, ApprovalStatus.PENDING)

    def test_membership_application_approval_and_rejection(self):
        applicant_user, applicant = self.create_member(
            "newbie@tw.test",
            status=MembershipStatus.PENDING,
            public=True,
        )
        # Pending member never appears on public Champions page even if public=True
        self.assertFalse(applicant.is_publicly_visible)
        self.assertEqual(
            self.client.get(f"/fa/champions/{applicant.slug}/").status_code, 404
        )

        # Club Manager approves membership application
        self.client.force_login(self.manager)
        resp = self.client.post(
            f"/fa/accounts/management/members/{applicant.pk}/",
            {
                "action": "review_membership",
                "membership_status": MembershipStatus.APPROVED,
                "admin_note": "خوش آمدید، عضویت شما تایید شد.",
            },
        )
        self.assertEqual(resp.status_code, 302)
        applicant.refresh_from_db()
        self.assertEqual(applicant.membership_status, MembershipStatus.APPROVED)
        self.assertTrue(applicant.is_publicly_visible)
        self.assertEqual(
            self.client.get(f"/fa/champions/{applicant.slug}/").status_code, 200
        )
        self.assertTrue(Notification.objects.filter(recipient=applicant_user).exists())
        self.assertTrue(
            AuditLog.objects.filter(action__contains="MEMBERSHIP").exists()
        )

    def test_belt_achievement_and_activity_submissions_create_pending_records(self):
        self.client.force_login(self.member_user)
        # Belt promotion
        r1 = self.client.post(
            "/fa/member/belts/add/",
            {
                "belt_type": self.belt.pk,
                "award_date": "2026-03-10",
                "issuing_authority": "Kukkiwon",
                "certificate": make_pdf_upload("dan.pdf"),
            },
        )
        self.assertEqual(r1.status_code, 302)
        self.assertEqual(self.member.belt_histories.get().approval_status, ApprovalStatus.PENDING)

        # Sports achievement
        r2 = self.client.post(
            "/fa/member/achievements/add/",
            {
                "title": "بهترین بازیکن فنی مسابقات",
                "discipline": Discipline.TAEKWONDO,
                "achievement_date": "2026-05-12",
                "description": "کسب عنوان فنی‌ترین مبارز مسابقات.",
            },
        )
        self.assertEqual(r2.status_code, 302)
        self.assertEqual(self.member.achievements.get().approval_status, ApprovalStatus.PENDING)

        # Social activity
        r3 = self.client.post(
            "/fa/member/activities/add/",
            {
                "title": "آموزش رایگان دفاع شخصی",
                "activity_date": "2026-06-01",
                "location": "تهران",
                "description": "برگزاری کارگاه آموزشی اجتماعی برای جوانان منطقه.",
                "public_visibility_consent": True,
            },
        )
        self.assertEqual(r3.status_code, 302)
        self.assertEqual(self.member.social_activities.get().approval_status, ApprovalStatus.PENDING)

"""End-to-end rendering and CRUD coverage across Member Portal and Custom Admin Portal templates."""
import datetime

from apps.accounts.models import UserRole
from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.belts.models import BeltHistory
from apps.competitions.models import CompetitionParticipation
from apps.contact.models import ContactMessage
from apps.core.models import ApprovalStatus, Discipline
from apps.medals.models import Medal, MedalType
from apps.notifications.models import Notification
from apps.pages.models import PageType
from apps.seo.models import SEOMetadata, SEOTranslation
from tests.base import TeakwondoTestCase, make_pdf_upload, make_png_upload


class PortalFullTemplateCoverageTests(TeakwondoTestCase):
    def setUp(self):
        self.super_admin = self.create_user("admin_ui@tw.test", role=UserRole.SUPER_ADMIN)
        self.member_user, self.member = self.create_member("athlete_ui@tw.test", public=True)
        self.belt = self.create_belt_type()
        self.comp = self.create_competition()
        self.post = self.create_bilingual_post("portal-post")
        self.product = self.create_bilingual_product("portal-product", "TW-UI-01")
        self.page = self.create_bilingual_page("about", PageType.ABOUT)
        self.seo = SEOMetadata.objects.create(route_key="pages:home")
        SEOTranslation.objects.create(
            seo=self.seo,
            language="fa",
            seo_title="تکواندو",
            seo_description="باشگاه هنرهای رزمی تکواندو",
        )
        self.contact = ContactMessage.objects.create(
            name="Visitor",
            email="v@example.com",
            subject="Schedule",
            message="Please share beginner training hours.",
            language="fa",
        )
        self.ach = Achievement.objects.create(
            member=self.member,
            title="قهرمان جام باشگاه‌ها",
            discipline=Discipline.TAEKWONDO,
            achievement_date=datetime.date(2026, 3, 1),
            certificate=make_pdf_upload("ach.pdf"),
        )
        self.medal = Medal.objects.create(
            member=self.member,
            medal_type=MedalType.GOLD,
            discipline=Discipline.TAEKWONDO,
            competition=self.comp,
            competition_name="مسابقات آسیا",
            competition_location="توکیو",
            award_date=datetime.date(2026, 5, 11),
            evidence=make_pdf_upload("med.pdf"),
        )
        self.bh = BeltHistory.objects.create(
            member=self.member,
            belt_type=self.belt,
            discipline=Discipline.TAEKWONDO,
            award_date=datetime.date(2026, 2, 10),
            certificate=make_pdf_upload("belt.pdf"),
        )
        self.part = CompetitionParticipation.objects.create(
            member=self.member,
            competition=self.comp,
            division_category="-68kg",
            result="اول",
            certificate=make_pdf_upload("part.pdf"),
        )
        self.act = SocialActivity.objects.create(
            member=self.member,
            title="سمینار داوطلبانه",
            description="آموزش رایگان برای نوجوانان.",
            activity_date=datetime.date(2026, 4, 15),
            location="تهران",
            public_visibility_consent=True,
            photograph=make_png_upload("act.png"),
        )
        self.notif = Notification.objects.create(
            recipient=self.member_user,
            message="رکورد شما در انتظار بررسی است.",
            message_ko="申請は審査待ちです。",
            target_url=self.medal.get_member_url(),
        )

    def test_all_member_portal_screens_render_in_fa_and_ko(self):
        self.client.force_login(self.member_user)
        paths = [
            "/member/dashboard/",
            "/member/profile/",
            "/member/settings/",
            "/member/settings/password/",
            "/member/achievements/",
            "/member/achievements/add/",
            f"/member/achievements/{self.ach.pk}/",
            f"/member/achievements/{self.ach.pk}/edit/",
            f"/member/achievements/{self.ach.pk}/delete/",
            "/member/medals/",
            "/member/medals/add/",
            f"/member/medals/{self.medal.pk}/",
            f"/member/medals/{self.medal.pk}/edit/",
            f"/member/medals/{self.medal.pk}/delete/",
            "/member/belts/",
            "/member/belts/add/",
            f"/member/belts/{self.bh.pk}/",
            f"/member/belts/{self.bh.pk}/edit/",
            f"/member/belts/{self.bh.pk}/delete/",
            "/member/competitions/",
            "/member/competitions/add/",
            f"/member/competitions/{self.part.pk}/",
            f"/member/competitions/{self.part.pk}/edit/",
            f"/member/competitions/{self.part.pk}/delete/",
            "/member/activities/",
            "/member/activities/add/",
            f"/member/activities/{self.act.pk}/",
            f"/member/activities/{self.act.pk}/edit/",
            f"/member/activities/{self.act.pk}/delete/",
            "/member/notifications/",
        ]
        for lang in ("fa", "ko"):
            for p in paths:
                url = f"/{lang}{p}"
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Failed GET {url}")

        # Approved record renders correction request page
        self.ach.approval_status = ApprovalStatus.APPROVED
        self.ach.save()
        self.assertEqual(
            self.client.get(f"/fa/member/achievements/{self.ach.pk}/request-correction/").status_code,
            200,
        )

    def test_all_admin_portal_screens_render_in_fa_and_ko(self):
        self.client.force_login(self.super_admin)
        paths = [
            "/accounts/management/",
            "/accounts/management/moderation/",
            f"/accounts/management/moderation/achievement/{self.ach.pk}/",
            f"/accounts/management/moderation/medal/{self.medal.pk}/",
            f"/accounts/management/moderation/belthistory/{self.bh.pk}/",
            f"/accounts/management/moderation/competitionparticipation/{self.part.pk}/",
            f"/accounts/management/moderation/socialactivity/{self.act.pk}/",
            "/accounts/management/members/",
            "/accounts/management/members/add/",
            f"/accounts/management/members/{self.member.pk}/",
            "/member/belts/admin-types/",
            "/member/belts/admin-types/add/",
            f"/member/belts/admin-types/{self.belt.pk}/edit/",
            "/member/competitions/manage/",
            "/member/competitions/manage/add/",
            f"/member/competitions/manage/{self.comp.pk}/edit/",
            "/blog/manage/",
            "/blog/manage/add/",
            f"/blog/manage/{self.post.pk}/edit/",
            "/blog/manage/categories/",
            "/blog/manage/categories/add/",
            f"/blog/manage/categories/{self.post.category_id}/edit/",
            "/products/manage/",
            "/products/manage/add/",
            f"/products/manage/{self.product.pk}/edit/",
            "/products/manage/categories/",
            "/products/manage/categories/add/",
            f"/products/manage/categories/{self.product.category_id}/edit/",
            "/pages/manage/",
            "/pages/manage/add/",
            f"/pages/manage/{self.page.pk}/edit/",
            "/management/seo/",
            "/management/seo/add/",
            f"/management/seo/{self.seo.pk}/edit/",
            "/contact/manage/",
            f"/contact/manage/{self.contact.pk}/",
            "/management/audit-logs/",
            "/management/audit-logs/reviews/",
        ]
        for lang in ("fa", "ko"):
            for p in paths:
                url = f"/{lang}{p}"
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200, f"Failed GET {url}")

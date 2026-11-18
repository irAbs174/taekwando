"""Public pages, Champions search/filters, content publication rules, and privacy leak tests."""
import datetime

from django.core import cache
from django.utils import timezone

from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.belts.models import BeltHistory
from apps.contact.models import ContactMessage
from apps.core.models import ApprovalStatus, Discipline, PublicationStatus
from apps.medals.models import Medal, MedalType
from tests.base import TechwandoTestCase, make_pdf_upload


class PublicPagesAndPrivacyTests(TechwandoTestCase):
    def setUp(self):
        cache.cache.clear()
        self.belt_dan = self.create_belt_type("DAN-2", 11, Discipline.TAEKWONDO, is_black=True)
        self.belt_karate = self.create_belt_type("KAR-1", 10, Discipline.KARATE, is_black=True)
        self.comp = self.create_competition("tokyo-grand-prix", Discipline.TAEKWONDO)

        # Public champion 1 (Taekwondo Gold)
        _, self.champ_tkd = self.create_member(
            "secret_email_tkd@tw.test",
            first_name="آرمان",
            last_name="شریفی",
            first_name_ja="アルマン",
            last_name_ja="シャリフィ",
            public=True,
            discipline=Discipline.TAEKWONDO,
            phone="+989129998877",
            birth_date=datetime.date(1997, 8, 23),
        )
        BeltHistory.objects.create(
            member=self.champ_tkd,
            belt_type=self.belt_dan,
            discipline=Discipline.TAEKWONDO,
            award_date=datetime.date(2025, 4, 1),
            approval_status=ApprovalStatus.APPROVED,
            certificate=make_pdf_upload("secret_belt_cert.pdf"),
        )
        Medal.objects.create(
            member=self.champ_tkd,
            medal_type=MedalType.GOLD,
            discipline=Discipline.TAEKWONDO,
            competition=self.comp,
            competition_name="گرندپری توکیو",
            award_date=datetime.date(2026, 5, 11),
            approval_status=ApprovalStatus.APPROVED,
            evidence=make_pdf_upload("secret_medal_cert.pdf"),
        )
        Medal.objects.create(
            member=self.champ_tkd,
            medal_type=MedalType.SILVER,
            discipline=Discipline.TAEKWONDO,
            competition_name="مسابقه تاییدنشده مخفی",
            award_date=datetime.date(2026, 6, 1),
            approval_status=ApprovalStatus.PENDING,
        )
        Achievement.objects.create(
            member=self.champ_tkd,
            title="فنی‌ترین تکواندوکار سال",
            discipline=Discipline.TAEKWONDO,
            achievement_date=datetime.date(2026, 5, 12),
            approval_status=ApprovalStatus.APPROVED,
        )
        # Approved activity WITHOUT public consent must remain hidden
        SocialActivity.objects.create(
            member=self.champ_tkd,
            title="فعالیت خصوصی بدون رضایت انتشار",
            description="توضیحات خصوصی",
            activity_date=datetime.date(2026, 3, 1),
            location="تهران",
            public_visibility_consent=False,
            approval_status=ApprovalStatus.APPROVED,
        )

        # Public champion 2 (Karate Bronze)
        _, self.champ_kar = self.create_member(
            "karateka@tw.test",
            first_name="هاروکا",
            last_name="تاناکا",
            public=True,
            discipline=Discipline.KARATE,
        )
        BeltHistory.objects.create(
            member=self.champ_kar,
            belt_type=self.belt_karate,
            discipline=Discipline.KARATE,
            award_date=datetime.date(2025, 1, 1),
            approval_status=ApprovalStatus.APPROVED,
        )
        Medal.objects.create(
            member=self.champ_kar,
            medal_type=MedalType.BRONZE,
            discipline=Discipline.KARATE,
            competition_name="جام کاراته اوزاکا",
            award_date=datetime.date(2025, 9, 10),
            approval_status=ApprovalStatus.APPROVED,
        )

        # Private approved member (consent=False) — must NEVER appear publicly
        _, self.private_member = self.create_member(
            "private@tw.test",
            first_name="مهسا",
            last_name="پنهان",
            public=False,
        )
        Medal.objects.create(
            member=self.private_member,
            medal_type=MedalType.GOLD,
            discipline=Discipline.JUDO,
            competition_name="مدال عضو خصوصی",
            award_date=datetime.date(2026, 4, 1),
            approval_status=ApprovalStatus.APPROVED,
        )

    def test_champions_search_filtering_and_sorting(self):
        # All public champions listed; private member excluded
        all_resp = self.client.get("/fa/champions/")
        self.assertContains(all_resp, "آرمان شریفی")
        self.assertContains(all_resp, "هاروکا تاناکا")
        self.assertNotContains(all_resp, "مهسا پنهان")

        # Search by name
        q_resp = self.client.get("/fa/champions/?q=آرمان")
        self.assertContains(q_resp, "آرمان شریفی")
        self.assertNotContains(q_resp, "هاروکا تاناکا")

        # Filter by discipline
        d_resp = self.client.get("/fa/champions/?discipline=KARATE")
        self.assertContains(d_resp, "هاروکا تاناکا")
        self.assertNotContains(d_resp, "آرمان شریفی")

        # Filter by medal type
        m_resp = self.client.get("/fa/champions/?medal_type=GOLD")
        self.assertContains(m_resp, "آرمان شریفی")
        self.assertNotContains(m_resp, "هاروکا تاناکا")

        # Filter by belt rank & competition & sort by achievement date
        b_resp = self.client.get(
            f"/fa/champions/?belt={self.belt_dan.pk}&competition={self.comp.pk}&sort=-latest_achievement"
        )
        self.assertContains(b_resp, "آرمان شریفی")
        self.assertNotContains(b_resp, "هاروکا تاناکا")

    def test_champion_profile_never_exposes_private_fields_or_unapproved_items(self):
        resp = self.client.get(f"/fa/champions/{self.champ_tkd.slug}/")
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode("utf-8")

        # Public approved info shown
        self.assertIn("آرمان شریفی", html)
        self.assertIn("مسابقات آزاد آسیا ۲۰۲۶", html)
        self.assertIn("فنی‌ترین تکواندوکار سال", html)

        # Sensitive / private / unapproved fields NEVER exposed
        self.assertNotIn("secret_email_tkd@tw.test", html)
        self.assertNotIn("+989129998877", html)
        self.assertNotIn("9129998877", html)
        self.assertNotIn("1997-08-23", html)
        self.assertNotIn("۱۹۹۷", html)
        self.assertNotIn("secret_medal_cert", html)
        self.assertNotIn("secret_belt_cert", html)
        self.assertNotIn("/protected-media/", html)
        self.assertNotIn("مسابقه تاییدنشده مخفی", html)
        self.assertNotIn("فعالیت خصوصی بدون رضایت انتشار", html)

        # Private member profile returns 404 and their medal never shows on Medal Winners
        self.assertEqual(
            self.client.get(f"/fa/champions/{self.private_member.slug}/").status_code,
            404,
        )
        self.assertNotContains(self.client.get("/fa/champions/medals/"), "مدال عضو خصوصی")

    def test_blog_draft_and_future_scheduled_hidden_and_product_optional_price(self):
        pub = self.create_bilingual_post("published-post", status=PublicationStatus.PUBLISHED)
        draft = self.create_bilingual_post("draft-post", status=PublicationStatus.DRAFT)
        future = self.create_bilingual_post(
            "future-post",
            status=PublicationStatus.SCHEDULED,
            published_at=timezone.now() + datetime.timedelta(days=7),
        )
        self.assertEqual(self.client.get(f"/fa/blog/{pub.slug}/").status_code, 200)
        self.assertEqual(self.client.get(f"/fa/blog/{draft.slug}/").status_code, 404)
        self.assertEqual(self.client.get(f"/fa/blog/{future.slug}/").status_code, 404)

        # Product without price renders cleanly with inquiry CTA (no online payment)
        custom = self.create_bilingual_product("custom-dan-belt", "TW-NOPRICE", price=None)
        prod_resp = self.client.get(f"/fa/products/{custom.slug}/")
        self.assertEqual(prod_resp.status_code, 200)
        self.assertContains(prod_resp, "TW-NOPRICE")

    def test_contact_form_stores_message_and_honeypot_blocks_bots(self):
        ok = self.client.post(
            "/ja/contact/",
            {
                "name": "山田 太郎",
                "email": "yamada@example.jp",
                "subject": "見学・体験稽古の希望",
                "message": "来週の土曜日にテコンドークラスの見学を希望しております。",
                "website": "",  # Empty honeypot
            },
        )
        self.assertEqual(ok.status_code, 302)
        msg = ContactMessage.objects.get(email="yamada@example.jp")
        self.assertEqual(msg.language, "ja")
        self.assertFalse(msg.is_read)

        # Bot filling honeypot rejected
        bot = self.client.post(
            "/ja/contact/",
            {
                "name": "SpamBot",
                "email": "spam@example.com",
                "subject": "Cheap links",
                "message": "Spam content filling honeypot field here.",
                "website": "https://spam.example.com",
            },
        )
        self.assertEqual(bot.status_code, 200)
        self.assertFalse(ContactMessage.objects.filter(email="spam@example.com").exists())

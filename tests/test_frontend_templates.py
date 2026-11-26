"""Smoke tests for the Bootstrap 5 frontend templates and language shells."""
from __future__ import annotations

import re

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from tests.base import DEFAULT_PASSWORD, TeakwondoTestCase


class PublicShellTests(TestCase):
    def test_niayesh_branding_and_map_address_render(self):
        for name in ("pages:home", "pages:about", "contact:public"):
            with translation.override("fa"):
                url = reverse(name)
            response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="fa")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "باشگاه تکواندو نیایش")

            if name != "pages:home":
                self.assertContains(
                    response,
                    "تهران | خیابان ولیعصر، بالاتر از چهارراه ولیعصر، کانون فرهنگی تربیتی نیایش",
                )
                self.assertContains(
                    response,
                    'href="https://maps.app.goo.gl/GACjRuq4QeXWjHSQ6"',
                )

    def test_persian_shell_is_rtl_and_uses_bootstrap_rtl(self):
        with translation.override("fa"):
            url = reverse("pages:home")
        response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="fa")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('<html lang="fa" dir="rtl">', html)
        self.assertIn("bootstrap.rtl.min.css", html)
        self.assertIn("/static/css/rtl.css", html)
        self.assertIn("/static/js/main.js", html)
        self.assertIn('class="skip-link"', html)

    def test_persian_homepage_uses_supplied_section_copy(self):
        response = self.client.get("/fa/", HTTP_ACCEPT_LANGUAGE="fa")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for copy in (
            "با مدیریت استاد امیر شاه آبادی فراهانی",
            "تکواندو سنت‌های رزمی ایرانی و بودوی کره‌ای را با علوم نوین ورزشی، ارتقای شفاف کمربند و سابقه تأییدشده هر دستاورد قهرمانی پیوند می‌دهد.",
            "قهرمانان باشگاه",
            "عضویت در باشگاه",
            "آکادمی در یک نگاه",
            "اعضای تاییدشده",
            "مدال‌های تاییدشده",
            "دارندگان کمربند مشکی",
            "حضور در مسابقات رسمی",
            "لزوم فراگیری تکواندو",
            "تکواندو ورزشی است که ریشه در احترام، تلاش و درستکاری دارد.",
            "از نخستین کلاس کودک تا آماده‌سازی برای مسابقات بین‌المللی",
            "داستان ما را بخوانید",
            "مشاهده برنامه درسی",
            "از مربیان باتجربه بیاموزید",
            "مربیان دارای گواهینامه با تجربه مسابقه، آموزش و صیانت از ورزشکاران.",
            "آشنایی با خانواده بزرگ نیایش",
            "افتخارات باشگاه",
            "تازه‌ترین افتخارات و مدال‌آوران",
            "تنها سوابقی در اینجا نمایش داده می‌شود که هیئت فنی تأیید کرده و مجوز نمایش عمومی دارند.",
            "تالار افتخارات مدال",
            "پروفایل ورزشکاران",
            "افتخارات و مدال‌های تأییدشده پس از ثبت در اینجا نمایش داده می‌شوند.",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, html)

    def test_persian_homepage_header_and_footer_match_reference(self):
        response = self.client.get("/fa/", HTTP_ACCEPT_LANGUAGE="fa")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for copy in (
            "آموزش, نظم و استمرار مقدمه تعالی",
            "درباره باشگاه تکواندو نیایش",
            "دسترسی سریع",
            "گالری تصاویر",
            "مدال‌آوران",
            "ثبت کمربندها",
            "درباره ما",
            "طراح و برنامه نویس",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, html)
        self.assertIn('href="https://damerchi.ir">طراح و برنامه نویس</a>', html)
        self.assertIn('href="/fa/about/">درباره ما</a>', html)

    def test_korean_homepage_uses_korean_section_copy(self):
        response = self.client.get("/ko/", HTTP_ACCEPT_LANGUAGE="ko")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        for copy in (
            "나이아쉬 태권도 클럽",
            "아미르 샤하바디 파라하니 사범이 지도합니다",
            "태권도는 페르시아 무술 전통과 한국 무도 전통을 현대 스포츠 과학, 투명한 승급 과정, 모든 대회 성과의 검증된 기록과 연결합니다.",
            "클럽 챔피언",
            "아카데미 한눈에 보기",
            "공식 대회 참가 횟수",
            "태권도를 배워야 하는 이유",
            "나이아쉬 가족을 만나보세요",
            "클럽 명예의 전당",
            "최근 성과와 메달 수상자",
            "메달 명예의 전당",
            "승인된 성과와 메달이 등록되면 여기에 표시됩니다.",
            "주요 탐색",
            "클럽 소개",
            "빠른 링크",
            "소셜 미디어",
            "기술 감독 및 수석 코치",
        ):
            with self.subTest(copy=copy):
                self.assertIn(copy, html)

    def test_korean_shell_is_ltr_and_uses_ko_typography(self):
        with translation.override("ko"):
            url = reverse("pages:home")
        response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="ko")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('<html lang="ko" dir="ltr">', html)
        self.assertIn("bootstrap.min.css", html)
        self.assertIn("/static/css/ko.css", html)

    def test_korean_typography_uses_korean_font_stack(self):
        css_path = finders.find("css/ko.css")
        self.assertIsNotNone(css_path)
        with open(css_path, encoding="utf-8") as handle:
            css = handle.read()
        self.assertIn('--tw-font-ko', css)
        self.assertIn('html[lang="ko"]', css)

    def test_public_pages_expose_one_h1_and_localized_metadata(self):
        for name, lang in (
            ("pages:about", "fa"),
            ("champions:list", "fa"),
            ("blog:list", "ko"),
            ("products:list", "ko"),
        ):
            with self.subTest(view=name, lang=lang):
                with translation.override(lang):
                    url = reverse(name)
                response = self.client.get(url, HTTP_ACCEPT_LANGUAGE=lang)
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertEqual(len(re.findall(r"<h1[\s>]", html)), 1)
                self.assertIn("hreflang=\"fa-IR\"", html)
                self.assertIn("hreflang=\"ko-KR\"", html)


class MemberPortalShellTests(TeakwondoTestCase):
    def test_member_dashboard_requires_authentication(self):
        url = reverse("members:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_member_dashboard_renders_sidebar_and_csrf(self):
        user, _profile = self.create_member("frontend.member@example.com")
        self.client.force_login(user)
        response = self.client.get(reverse("members:dashboard"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("dashboard-sidebar", html)
        self.assertIn("dashboard-offcanvas", html)
        self.assertIn("memberSidebar", html)
        self.assertIn("csrfmiddlewaretoken", html)
        self.assertNotIn("PRIVATE_MEDIA", html)

    def test_member_submission_forms_render_labels_and_csrf(self):
        user, _profile = self.create_member("frontend.forms@example.com")
        self.client.force_login(user)
        for name in (
            "achievements:member_add",
            "medals:member_add",
            "belts:member_add",
            "competitions:member_add",
            "activities:member_add",
        ):
            with self.subTest(view=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                html = response.content.decode()
                self.assertIn("csrfmiddlewaretoken", html)
                self.assertIn("<form", html)
                self.assertNotIn('type="password" autocomplete="current-password"', html)


class AdminPortalShellTests(TeakwondoTestCase):
    def test_member_cannot_reach_admin_portal(self):
        user, _profile = self.create_member("frontend.no-admin@example.com")
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_manager_sees_admin_shell_and_sidebar(self):
        manager = self.create_user("frontend.manager@example.com", role="CLUB_MANAGER")
        self.client.force_login(manager)
        response = self.client.get(reverse("accounts:admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("dashboard-shell", html)
        self.assertIn(reverse("accounts:admin_moderation_queue"), html)
        self.assertIn(reverse("audit_logs:list"), html)


class AccessibleFormTests(TestCase):
    def test_contact_validation_renders_linked_aria_errors(self):
        with translation.override("fa"):
            url = reverse("contact:public")
        response = self.client.post(
            url,
            {
                "name": "",
                "email": "not-an-email",
                "subject": "",
                "message": "short",
                "language": "fa",
            },
        )
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("field-has-error", html)
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_email_error"', html)
        self.assertIn('id="id_email_error"', html)

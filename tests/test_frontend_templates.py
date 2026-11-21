"""Smoke tests for the Bootstrap 5 frontend templates and language shells."""
from __future__ import annotations

import re

from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from tests.base import DEFAULT_PASSWORD, TechwandoTestCase


class PublicShellTests(TestCase):
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


class MemberPortalShellTests(TechwandoTestCase):
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


class AdminPortalShellTests(TechwandoTestCase):
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

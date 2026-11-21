"""Authentication, registration, rate-limiting, and password management tests."""
from django.core import cache, mail
from django.urls import reverse

from apps.accounts.models import User, UserRole
from apps.audit_logs.models import AuditLog
from apps.members.models import MemberProfile, MembershipStatus
from apps.notifications.models import Notification
from tests.base import DEFAULT_PASSWORD, TeakwondoTestCase


class AuthenticationTests(TeakwondoTestCase):
    def setUp(self):
        cache.cache.clear()
        self.manager = self.create_user(
            "manager@teakwondo.test", role=UserRole.CLUB_MANAGER
        )

    def test_public_registration_creates_member_and_blocks_role_escalation(self):
        url = "/fa/accounts/register/"
        resp = self.client.post(
            url,
            {
                "first_name": "سارا",
                "last_name": "کریمی",
                "email": "Sara.Karimi@Teakwondo.Test",
                "primary_discipline": "TAEKWONDO",
                "preferred_language": "fa",
                "password1": DEFAULT_PASSWORD,
                "password2": DEFAULT_PASSWORD,
                "agree_terms": "on",
                # Malicious privilege-escalation fields MUST be ignored
                "role": UserRole.SUPER_ADMIN,
                "is_staff": "true",
                "is_superuser": "true",
                "membership_status": MembershipStatus.APPROVED,
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp["Location"].endswith("/member/dashboard/"))

        user = User.objects.get(email="sara.karimi@teakwondo.test")
        self.assertEqual(user.role, UserRole.MEMBER)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(DEFAULT_PASSWORD))

        profile = MemberProfile.objects.get(user=user)
        self.assertTrue(profile.membership_number.startswith("TW-"))
        self.assertEqual(profile.membership_status, MembershipStatus.PENDING)
        self.assertFalse(profile.public_profile_visibility)

        # Admin notification + AuditLog recorded
        self.assertTrue(Notification.objects.filter(recipient=self.manager).exists())
        self.assertTrue(AuditLog.objects.filter(action__contains="REGISTER").exists())

    def test_duplicate_email_registration_rejected(self):
        self.create_member("dup@teakwondo.test")
        resp = self.client.post(
            "/ko/accounts/register/",
            {
                "first_name": "健太",
                "last_name": "佐藤",
                "email": "DUP@teakwondo.test",
                "primary_discipline": "KARATE",
                "preferred_language": "ko",
                "password1": DEFAULT_PASSWORD,
                "password2": DEFAULT_PASSWORD,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="dup@teakwondo.test").count(), 1)

    def test_login_logout_post_only_and_role_redirects(self):
        user, _ = self.create_member("athlete@teakwondo.test")
        resp = self.client.post(
            "/fa/accounts/login/",
            {"email": "athlete@teakwondo.test", "password": DEFAULT_PASSWORD},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.redirect_chain[-1][0].endswith("/member/dashboard/"))

        # GET logout must be rejected (405 Method Not Allowed) to prevent CSRF logout
        get_logout = self.client.get("/fa/accounts/logout/")
        self.assertEqual(get_logout.status_code, 405)

        # POST logout succeeds
        post_logout = self.client.post("/fa/accounts/logout/")
        self.assertEqual(post_logout.status_code, 302)

        # Staff user redirects to admin dashboard
        admin_resp = self.client.post(
            "/ko/accounts/login/",
            {"email": "manager@teakwondo.test", "password": DEFAULT_PASSWORD},
            follow=True,
        )
        self.assertEqual(admin_resp.status_code, 200)
        self.assertIn("/accounts/management/", admin_resp.redirect_chain[-1][0])

    def test_inactive_account_cannot_login(self):
        self.create_user(
            "inactive@teakwondo.test", role=UserRole.MEMBER, is_active=False
        )
        resp = self.client.post(
            "/fa/accounts/login/",
            {"email": "inactive@teakwondo.test", "password": DEFAULT_PASSWORD},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.wsgi_request.user.is_authenticated)

    def test_login_brute_force_rate_limiting_blocks_repeated_failures(self):
        self.create_member("target@teakwondo.test")
        for _ in range(5):
            self.client.post(
                "/fa/accounts/login/",
                {"email": "target@teakwondo.test", "password": "WrongPassword123!"},
            )
        # 6th attempt even with CORRECT password must be blocked (429 Too Many Requests)
        locked_resp = self.client.post(
            "/fa/accounts/login/",
            {"email": "target@teakwondo.test", "password": DEFAULT_PASSWORD},
        )
        self.assertEqual(locked_resp.status_code, 429)
        self.assertFalse(locked_resp.wsgi_request.user.is_authenticated)

    def test_password_change_and_password_reset_flow(self):
        user, _ = self.create_member("resetme@teakwondo.test")
        self.client.force_login(user)

        new_pw = "Updated#Pass2026!Tw"
        change_resp = self.client.post(
            "/fa/member/settings/password/",
            {
                "old_password": DEFAULT_PASSWORD,
                "new_password1": new_pw,
                "new_password2": new_pw,
            },
        )
        self.assertEqual(change_resp.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_pw))

        # Now test password reset email generation
        self.client.logout()
        reset_resp = self.client.post(
            "/fa/accounts/password-reset/",
            {"email": "resetme@teakwondo.test"},
        )
        self.assertEqual(reset_resp.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("password-reset", mail.outbox[0].body)

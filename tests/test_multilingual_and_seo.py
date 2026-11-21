"""Multilingual (fa-IR RTL & ko-KR LTR), translation fallback, switcher, and SEO tests."""
from django.db import IntegrityError, transaction

from apps.blog.models import PostTranslation
from apps.pages.models import PageType
from tests.base import TechwandoTestCase


class MultilingualAndSEOTests(TechwandoTestCase):
    def setUp(self):
        self.about = self.create_bilingual_page("about", PageType.ABOUT)
        self.edu = self.create_bilingual_page("budo-basics", PageType.EDUCATION)
        self.prog = self.create_bilingual_page("sparring-squad", PageType.SERVICE)
        self.post = self.create_bilingual_post("poomsae-mastery", include_ko=True)
        self.fa_only_post = self.create_bilingual_post("persian-only-guide", include_ko=False)
        self.product = self.create_bilingual_product("pro-dobok", "TW-SEO-01", price="12500")
        self.member_user, self.champion = self.create_member("champ_i18n@tw.test", public=True)

    def test_persian_rtl_and_korean_ltr_localized_routes(self):
        fa_routes = [
            "/fa/",
            "/fa/about/",
            "/fa/education/",
            "/fa/services/",
            "/fa/blog/",
            f"/fa/blog/{self.post.slug}/",
            "/fa/champions/",
            f"/fa/champions/{self.champion.slug}/",
            "/fa/champions/medals/",
            "/fa/champions/belts/",
            "/fa/champions/competitions/",
            "/fa/products/",
            f"/fa/products/{self.product.slug}/",
            "/fa/contact/",
            "/fa/accounts/login/",
            "/fa/accounts/register/",
        ]
        for route in fa_routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Persian route failed: {route}")
            html = resp.content.decode("utf-8")
            self.assertIn('lang="fa"', html)
            self.assertIn('dir="rtl"', html)
            self.assertIn("rtl.css", html)

        ko_routes = [r.replace("/fa/", "/ko/", 1) for r in fa_routes]
        for route in ko_routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Korean route failed: {route}")
            html = resp.content.decode("utf-8")
            self.assertIn('lang="ko"', html)
            self.assertIn('dir="ltr"', html)
            self.assertIn("ko.css", html)

        # Authenticated member localized dashboard routes
        self.client.force_login(self.member_user)
        fa_dash = self.client.get("/fa/member/dashboard/")
        ko_dash = self.client.get("/ko/member/dashboard/")
        self.assertEqual(fa_dash.status_code, 200)
        self.assertEqual(ko_dash.status_code, 200)
        self.assertContains(fa_dash, 'dir="rtl"')
        self.assertContains(ko_dash, 'dir="ltr"')

    def test_gettext_ui_and_database_translations_plus_persian_numerals(self):
        fa_blog = self.client.get(f"/fa/blog/{self.post.slug}/")
        self.assertContains(fa_blog, "اصول پومسه پیشرفته")
        self.assertContains(fa_blog, "قهرمانان")  # Gettext Persian navbar

        ko_blog = self.client.get(f"/ko/blog/{self.post.slug}/")
        self.assertContains(ko_blog, "고급 품새의 핵심")
        self.assertContains(ko_blog, "챔피언")  # Gettext Korean navbar

        # Persian numerals on Persian product price vs standard numerals on Korean
        fa_prod = self.client.get(f"/fa/products/{self.product.slug}/")
        ko_prod = self.client.get(f"/ko/products/{self.product.slug}/")
        self.assertContains(fa_prod, "۱۲٬۵۰۰")
        self.assertContains(ko_prod, "12,500")

    def test_unique_translation_constraint_and_graceful_fallback(self):
        # Cannot duplicate (post, language)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PostTranslation.objects.create(
                    post=self.post, language="fa", title="تکراری", body="متن"
                )

        # Visiting /ko/ for a post that only has a Persian translation falls back cleanly
        ko_fallback = self.client.get(f"/ko/blog/{self.fa_only_post.slug}/")
        self.assertEqual(ko_fallback.status_code, 200)
        self.assertContains(ko_fallback, "اصول پومسه پیشرفته")
        self.assertContains(ko_fallback, "번역이 없어 제공 가능한 언어로 표시합니다.")

    def test_language_switcher_updates_url_cookie_and_user_preference(self):
        self.client.force_login(self.member_user)
        resp = self.client.post(
            "/switch-language/",
            {"language": "ko", "next": "/fa/products/"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/ko/products/")
        self.member_user.refresh_from_db()
        self.assertEqual(self.member_user.preferred_language, "ko")

        # Open-redirect protection: external URL rejected and redirected safely to /ko/
        evil = self.client.post(
            "/switch-language/",
            {"language": "ko", "next": "https://evil.example.org/phish"},
        )
        self.assertEqual(evil.status_code, 302)
        self.assertNotIn("evil.example.org", evil["Location"])

    def test_seo_meta_hreflang_jsonld_robots_and_sitemap(self):
        resp = self.client.get(f"/fa/blog/{self.post.slug}/")
        html = resp.content.decode("utf-8")
        self.assertIn("آموزش پومسه | تکواندو", html)
        self.assertIn('name="description" content="توضیحات سئو پومسه فارسی."', html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('hreflang="fa-IR"', html)
        self.assertIn('hreflang="ko-KR"', html)
        self.assertIn('hreflang="x-default"', html)
        self.assertIn('property="og:title"', html)
        self.assertIn('property="og:locale" content="fa_IR"', html)
        self.assertIn("application/ld+json", html)
        self.assertIn('"@type": "BlogPosting"', html)

        # robots.txt
        robots = self.client.get("/robots.txt")
        self.assertEqual(robots.status_code, 200)
        rtxt = robots.content.decode("utf-8")
        self.assertIn("Sitemap:", rtxt)
        self.assertIn("Disallow: /fa/member/", rtxt)
        self.assertIn("Disallow: /protected-media/", rtxt)

        # XML sitemap
        smap = self.client.get("/sitemap.xml")
        self.assertEqual(smap.status_code, 200)
        sxml = smap.content.decode("utf-8")
        self.assertIn(f"/fa/blog/{self.post.slug}/", sxml)
        self.assertIn(f"/ko/blog/{self.post.slug}/", sxml)
        self.assertIn(f"/fa/products/{self.product.slug}/", sxml)
        self.assertIn(f"/fa/champions/{self.champion.slug}/", sxml)

    def test_legacy_japanese_is_not_shown_as_korean(self):
        from apps.core.translation_utils import resolve_translation
        from apps.belts.models import BeltType
        from apps.core.models import Discipline
        from django.utils import translation

        self.fa_only_post.translations.create(
            language="ja", title="日本語の旧記事", body="旧本文"
        )
        selected = resolve_translation(self.fa_only_post, "ko")
        self.assertEqual(selected.language, "fa")
        self.assertTrue(selected.is_fallback)
        response = self.client.get(f"/ko/blog/{self.fa_only_post.slug}/")
        self.assertNotContains(response, "日本語の旧記事")
        self.assertContains(response, "اصول پومسه پیشرفته")

        belt = BeltType.objects.create(
            discipline=Discipline.TAEKWONDO, rank_code="test-ko", rank_order=50,
            name_fa="کمربند", name_ja="古い帯", name_ko="한국어 띠",
        )
        with translation.override("ko"):
            self.assertEqual(belt.localized_name, "한국어 띠")
        belt.refresh_from_db()
        self.assertEqual(belt.name_ja, "古い帯")

    def test_korean_dates_and_no_japanese_route(self):
        import datetime
        from django.utils import translation
        from apps.core.templatetags.techwando_tags import local_date

        with translation.override("ko"):
            self.assertEqual(local_date(datetime.date(2026, 11, 21)), "2026년 11월 21일")
        self.assertEqual(self.client.get("/ja/").status_code, 404)
        self.assertContains(self.client.get("/ko/"), "한국어")

"""Multilingual (fa-IR RTL & ja-JP LTR), translation fallback, switcher, and SEO tests."""
from django.db import IntegrityError, transaction

from apps.blog.models import PostTranslation
from apps.pages.models import PageType
from tests.base import TechwandoTestCase


class MultilingualAndSEOTests(TechwandoTestCase):
    def setUp(self):
        self.about = self.create_bilingual_page("about", PageType.ABOUT)
        self.edu = self.create_bilingual_page("budo-basics", PageType.EDUCATION)
        self.prog = self.create_bilingual_page("sparring-squad", PageType.SERVICE)
        self.post = self.create_bilingual_post("poomsae-mastery", include_ja=True)
        self.fa_only_post = self.create_bilingual_post("persian-only-guide", include_ja=False)
        self.product = self.create_bilingual_product("pro-dobok", "TW-SEO-01", price="12500")
        self.member_user, self.champion = self.create_member("champ_i18n@tw.test", public=True)

    def test_persian_rtl_and_japanese_ltr_localized_routes(self):
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

        ja_routes = [r.replace("/fa/", "/ja/", 1) for r in fa_routes]
        for route in ja_routes:
            resp = self.client.get(route)
            self.assertEqual(resp.status_code, 200, f"Japanese route failed: {route}")
            html = resp.content.decode("utf-8")
            self.assertIn('lang="ja"', html)
            self.assertIn('dir="ltr"', html)
            self.assertIn("ja.css", html)

        # Authenticated member localized dashboard routes
        self.client.force_login(self.member_user)
        fa_dash = self.client.get("/fa/member/dashboard/")
        ja_dash = self.client.get("/ja/member/dashboard/")
        self.assertEqual(fa_dash.status_code, 200)
        self.assertEqual(ja_dash.status_code, 200)
        self.assertContains(fa_dash, 'dir="rtl"')
        self.assertContains(ja_dash, 'dir="ltr"')

    def test_gettext_ui_and_database_translations_plus_persian_numerals(self):
        fa_blog = self.client.get(f"/fa/blog/{self.post.slug}/")
        self.assertContains(fa_blog, "اصول پومسه پیشرفته")
        self.assertContains(fa_blog, "قهرمانان")  # Gettext Persian navbar

        ja_blog = self.client.get(f"/ja/blog/{self.post.slug}/")
        self.assertContains(ja_blog, "上級プムセの極意")
        self.assertContains(ja_blog, "チャンピオン")  # Gettext Japanese navbar

        # Persian numerals on Persian product price vs standard numerals on Japanese
        fa_prod = self.client.get(f"/fa/products/{self.product.slug}/")
        ja_prod = self.client.get(f"/ja/products/{self.product.slug}/")
        self.assertContains(fa_prod, "۱۲٬۵۰۰")
        self.assertContains(ja_prod, "12,500")

    def test_unique_translation_constraint_and_graceful_fallback(self):
        # Cannot duplicate (post, language)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PostTranslation.objects.create(
                    post=self.post, language="fa", title="تکراری", body="متن"
                )

        # Visiting /ja/ for a post that only has a Persian translation falls back cleanly
        ja_fallback = self.client.get(f"/ja/blog/{self.fa_only_post.slug}/")
        self.assertEqual(ja_fallback.status_code, 200)
        self.assertContains(ja_fallback, "اصول پومسه پیشرفته")
        self.assertContains(ja_fallback, "フォールバック表示")

    def test_language_switcher_updates_url_cookie_and_user_preference(self):
        self.client.force_login(self.member_user)
        resp = self.client.post(
            "/switch-language/",
            {"language": "ja", "next": "/fa/products/"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], "/ja/products/")
        self.member_user.refresh_from_db()
        self.assertEqual(self.member_user.preferred_language, "ja")

        # Open-redirect protection: external URL rejected and redirected safely to /ja/
        evil = self.client.post(
            "/switch-language/",
            {"language": "ja", "next": "https://evil.example.org/phish"},
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
        self.assertIn('hreflang="ja-JP"', html)
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
        self.assertIn(f"/ja/blog/{self.post.slug}/", sxml)
        self.assertIn(f"/fa/products/{self.product.slug}/", sxml)
        self.assertIn(f"/fa/champions/{self.champion.slug}/", sxml)

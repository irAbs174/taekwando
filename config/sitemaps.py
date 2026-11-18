"""Multilingual (fa & ja) XML sitemaps with xhtml:link hreflang alternates."""
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from apps.blog.models import Post
from apps.members.models import MemberProfile
from apps.pages.models import Page
from apps.products.models import Product


class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = "weekly"
    i18n = True
    alternates = True
    languages = ["fa", "ja"]

    def items(self):
        return [
            "pages:home",
            "pages:about",
            "pages:education",
            "pages:services",
            "blog:list",
            "products:list",
            "champions:list",
            "champions:medals",
            "champions:belts",
            "champions:competitions",
            "contact:public",
        ]

    def location(self, item):
        return reverse(item)


class BlogPostSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"
    i18n = True
    alternates = True
    languages = ["fa", "ja"]

    def items(self):
        return Post.objects.published().filter(robots_index=True).order_by("-published_at")

    def lastmod(self, obj: Post):
        return obj.updated_at


class ProductSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"
    i18n = True
    alternates = True
    languages = ["fa", "ja"]

    def items(self):
        return Product.objects.published().filter(robots_index=True).order_by("-updated_at")

    def lastmod(self, obj: Product):
        return obj.updated_at


class ChampionSitemap(Sitemap):
    priority = 0.6
    changefreq = "weekly"
    i18n = True
    alternates = True
    languages = ["fa", "ja"]

    def items(self):
        return MemberProfile.objects.publicly_visible().order_by("-updated_at")

    def location(self, obj: MemberProfile):
        return obj.get_public_url()

    def lastmod(self, obj: MemberProfile):
        return obj.updated_at


class StaticPageSitemap(Sitemap):
    priority = 0.6
    changefreq = "monthly"
    i18n = True
    alternates = True
    languages = ["fa", "ja"]

    def items(self):
        return (
            Page.objects.published()
            .filter(robots_index=True)
            .exclude(slug="about")
            .order_by("display_order")
        )

    def lastmod(self, obj: Page):
        return obj.updated_at


SITEMAPS = {
    "static": StaticViewSitemap,
    "blog": BlogPostSitemap,
    "products": ProductSitemap,
    "champions": ChampionSitemap,
    "pages": StaticPageSitemap,
}

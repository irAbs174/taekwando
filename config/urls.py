"""Root URL configuration for TECHWANDO with localized /fa/ and /ko/ routing."""
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path

from apps.core.views import BlockedPrivateMediaPathView, RootLanguageRedirectView
from apps.seo.views import RobotsTxtView
from config.sitemaps import SITEMAPS

# Non-localized system, SEO, API, admin, and security routes
urlpatterns = [
    path("", RootLanguageRedirectView.as_view(), name="root_redirect"),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", include("apps.core.urls")),
    path("robots.txt", RobotsTxtView.as_view(), name="robots_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    # Versioned REST API & OpenAPI documentation
    path("api/v1/", include("apps.api.urls")),
    # Customized Django Admin (path configurable via DJANGO_ADMIN_URL)
    path(settings.DJANGO_ADMIN_URL, admin.site.urls),
    # Hard defense-in-depth block against direct URL guessing of sensitive directories
    re_path(
        r"^media/(certificates|medals|activities)/.*$",
        BlockedPrivateMediaPathView.as_view(),
        name="blocked_private_media",
    ),
]

# Localized Persian (/fa/) and Korean (/ko/) public, member, and management routes
urlpatterns += i18n_patterns(
    path("", include("apps.pages.urls")),
    path("blog/", include("apps.blog.urls")),
    path("products/", include("apps.products.urls")),
    path("champions/", include("apps.members.public_urls")),
    path("contact/", include("apps.contact.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("member/", include("apps.members.urls")),
    path("member/achievements/", include("apps.achievements.urls")),
    path("member/medals/", include("apps.medals.urls")),
    path("member/belts/", include("apps.belts.urls")),
    path("member/competitions/", include("apps.competitions.urls")),
    path("member/activities/", include("apps.activities.urls")),
    path("member/notifications/", include("apps.notifications.urls")),
    path("management/seo/", include("apps.seo.urls")),
    path("management/audit-logs/", include("apps.audit_logs.urls")),
    prefix_default_language=True,
)

# In local development only, serve non-sensitive public uploads (profiles, blog, products, seo)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"

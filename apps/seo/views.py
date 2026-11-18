"""Views for robots.txt and custom admin bilingual SEO management."""
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.audit_logs.services import log_audit_event
from apps.core.permissions import ContentAdminMixin
from apps.seo.forms import RouteSEOBilingualForm
from apps.seo.models import SEOMetadata


class RobotsTxtView(View):
    """Serve SEO-friendly robots.txt referencing sitemap and protecting private paths."""

    def get(self, request):
        base = settings.SITE_BASE_URL or f"{request.scheme}://{request.get_host()}"
        admin_prefix = settings.DJANGO_ADMIN_URL
        lines = [
            "User-agent: *",
            "Allow: /fa/",
            "Allow: /ja/",
            f"Disallow: /{admin_prefix}",
            "Disallow: /fa/member/",
            "Disallow: /ja/member/",
            "Disallow: /fa/management/",
            "Disallow: /ja/management/",
            "Disallow: /fa/*/manage/",
            "Disallow: /ja/*/manage/",
            "Disallow: /fa/accounts/",
            "Disallow: /ja/accounts/",
            "Disallow: /protected-media/",
            "Disallow: /private-media/",
            "Disallow: /api/v1/member/",
            "Disallow: /api/v1/admin/",
            "",
            f"Sitemap: {base}/sitemap.xml",
            "",
        ]
        return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


class AdminSEOListView(ContentAdminMixin, ListView):
    model = SEOMetadata
    template_name = "dashboard/admin/seo_list.html"
    context_object_name = "seo_entries"
    paginate_by = 25

    def get_queryset(self):
        return SEOMetadata.objects.prefetch_related("translations").order_by("route_key", "-id")


class AdminSEOCreateView(ContentAdminMixin, CreateView):
    model = SEOMetadata
    form_class = RouteSEOBilingualForm
    template_name = "dashboard/admin/seo_form.html"
    success_url = reverse_lazy("seo:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="SEO_CREATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("SEO metadata saved."))
        return resp


class AdminSEOUpdateView(ContentAdminMixin, UpdateView):
    model = SEOMetadata
    form_class = RouteSEOBilingualForm
    template_name = "dashboard/admin/seo_form.html"
    success_url = reverse_lazy("seo:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="SEO_UPDATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("SEO metadata updated."))
        return resp

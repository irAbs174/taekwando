"""Public homepage, about, education, training programs, and page admin views."""
from __future__ import annotations

from django.contrib import messages
from django.db import transaction
from django.db.models import Count, Q
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.audit_logs.services import log_audit_event
from apps.belts.models import BeltHistory
from apps.blog.models import Post
from apps.competitions.models import Competition
from apps.core.models import ApprovalStatus
from apps.core.permissions import ContentAdminMixin
from apps.medals.models import Medal
from apps.members.models import MemberProfile
from apps.pages.forms import PageBilingualForm
from apps.pages.models import Page, PageType
from apps.products.models import Product
from apps.seo.models import RouteKey
from apps.seo.services import build_seo_context


class HomePageView(TemplateView):
    template_name = "public/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        champions = (
            MemberProfile.objects.publicly_visible()
            .annotate(
                approved_medal_count=Count(
                    "medals",
                    filter=Q(medals__approval_status=ApprovalStatus.APPROVED),
                    distinct=True,
                ),
                gold_count=Count(
                    "medals",
                    filter=Q(
                        medals__approval_status=ApprovalStatus.APPROVED,
                        medals__medal_type="GOLD",
                    ),
                    distinct=True,
                ),
            )
            .order_by("-gold_count", "-approved_medal_count", "last_name")[:4]
        )

        recent_medals = (
            Medal.objects.publicly_visible()
            .select_related("member", "competition")
            .order_by("-award_date", "-id")[:6]
        )

        recent_achievements = (
            Achievement.objects.publicly_visible()
            .select_related("member")
            .order_by("-achievement_date", "-id")[:4]
        )

        recent_activities = (
            SocialActivity.objects.publicly_visible()
            .select_related("member")
            .order_by("-activity_date", "-id")[:3]
        )

        latest_posts = (
            Post.objects.published()
            .select_related("category")
            .prefetch_related("translations", "category__translations")
            .order_by("-is_featured", "-published_at")[:3]
        )

        featured_products = (
            Product.objects.published()
            .prefetch_related("translations", "images")
            .order_by("-is_featured", "-created_at")[:4]
        )

        services = (
            Page.objects.published()
            .filter(page_type=PageType.SERVICE)
            .prefetch_related("translations")[:3]
        )

        education_modules = (
            Page.objects.published()
            .filter(page_type=PageType.EDUCATION)
            .prefetch_related("translations")[:3]
        )

        ctx.update(
            {
                "featured_champions": champions,
                "recent_medals": recent_medals,
                "recent_achievements": recent_achievements,
                "recent_activities": recent_activities,
                "latest_posts": latest_posts,
                "featured_products": featured_products,
                "services": services,
                "education_modules": education_modules,
                "stats": {
                    "active_members": MemberProfile.objects.approved_members().count(),
                    "approved_medals": Medal.objects.publicly_visible().count(),
                    "black_belts": BeltHistory.objects.publicly_visible()
                    .filter(belt_type__is_black_belt=True)
                    .values("member_id")
                    .distinct()
                    .count(),
                    "competitions": Competition.objects.filter(is_published=True).count(),
                },
            }
        )
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.HOME,
                default_title=_("Martial Arts Academy, Champions & Club Platform"),
            )
        )
        return ctx


class AboutPageView(TemplateView):
    template_name = "public/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = (
            Page.objects.published()
            .prefetch_related("translations")
            .filter(Q(slug="about") | Q(page_type=PageType.ABOUT))
            .first()
        )
        page_tr = page.get_translation(self.request.LANGUAGE_CODE) if page else None
        ctx["page"] = page
        ctx["page_tr"] = page_tr
        ctx["services"] = (
            Page.objects.published()
            .filter(page_type=PageType.SERVICE)
            .prefetch_related("translations")[:4]
        )
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.ABOUT,
                default_title=(page_tr.seo_title or page_tr.title)
                if page_tr
                else _("About TECHWANDO"),
                default_description=(page_tr.seo_description or page_tr.summary)
                if page_tr
                else _(
                    "Learn about TECHWANDO's martial arts philosophy, certified coaching "
                    "programs, athlete verification workflow, and Persian-Japanese cultural bridge."
                ),
            )
        )
        return ctx


class EducationPageView(ListView):
    model = Page
    template_name = "public/education.html"
    context_object_name = "modules"
    paginate_by = 12

    def get_queryset(self):
        return (
            Page.objects.published()
            .filter(page_type=PageType.EDUCATION)
            .prefetch_related("translations")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["recent_posts"] = (
            Post.objects.published().prefetch_related("translations")[:3]
        )
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.EDUCATION,
                default_title=_("Martial Arts Education & Curriculum"),
                default_description=_(
                    "Structured educational syllabus covering Poomsae, Kyorugi tactics, "
                    "etiquette (Reigi), sports nutrition, and belt examination criteria."
                ),
            )
        )
        return ctx


class ServicesPageView(ListView):
    model = Page
    template_name = "public/services.html"
    context_object_name = "programs"
    paginate_by = 12

    def get_queryset(self):
        return (
            Page.objects.published()
            .filter(page_type=PageType.SERVICE)
            .prefetch_related("translations")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.SERVICES,
                default_title=_("Martial Arts Services & Training Programs"),
                default_description=_(
                    "Youth fundamentals, competitive sparring squads, black belt Dan "
                    "preparation, and international training seminars at TECHWANDO."
                ),
            )
        )
        return ctx


class StaticPageDetailView(DetailView):
    model = Page
    template_name = "public/page_detail.html"
    context_object_name = "page"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Page.objects.published().prefetch_related("translations")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page: Page = self.object
        tr = page.get_translation(self.request.LANGUAGE_CODE)
        ctx["page_tr"] = tr
        title = (tr.seo_title or tr.title) if tr else page.slug
        desc = (tr.seo_description or tr.summary or tr.body[:180]) if tr else ""
        ctx.update(
            build_seo_context(
                self.request,
                default_title=title,
                default_description=desc,
                canonical_url=tr.canonical_url if tr else "",
                og_title=(tr.og_title or title) if tr else title,
                og_description=(tr.og_description or desc) if tr else desc,
                robots_index=page.robots_index,
                robots_follow=page.robots_follow,
            )
        )
        return ctx


class AdminPageListView(ContentAdminMixin, ListView):
    model = Page
    template_name = "dashboard/admin/page_list.html"
    context_object_name = "pages"
    paginate_by = 25

    def get_queryset(self):
        return Page.objects.prefetch_related("translations").order_by(
            "page_type", "display_order", "slug"
        )


class AdminPageCreateView(ContentAdminMixin, CreateView):
    model = Page
    form_class = PageBilingualForm
    template_name = "dashboard/admin/page_form.html"
    success_url = reverse_lazy("pages:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="PAGE_CREATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Page created successfully."))
        return resp


class AdminPageUpdateView(ContentAdminMixin, UpdateView):
    model = Page
    form_class = PageBilingualForm
    template_name = "dashboard/admin/page_form.html"
    success_url = reverse_lazy("pages:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="PAGE_UPDATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Page updated successfully."))
        return resp

class LegalPageMixin:
    """Base for the named privacy and terms routes backed by a Page record."""

    template_name = "public/legal.html"
    page_slug = ""
    legal_kind = ""
    default_title = ""
    default_description = ""

    def get_legal_page(self):
        return (
            Page.objects.published()
            .prefetch_related("translations")
            .filter(slug=self.page_slug)
            .first()
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        page = self.get_legal_page()
        tr = page.get_translation(self.request.LANGUAGE_CODE) if page else None
        ctx["legal_page"] = page
        ctx["legal_tr"] = tr
        ctx["legal_kind"] = self.legal_kind
        title = self.default_title
        if tr:
            title = tr.seo_title or tr.title or title
        description = self.default_description
        if tr:
            description = tr.seo_description or tr.summary or description
        ctx.update(
            build_seo_context(
                self.request,
                default_title=title,
                default_description=description,
            )
        )
        return ctx


class PrivacyPageView(LegalPageMixin, TemplateView):
    template_name = "public/privacy.html"
    page_slug = "privacy-policy"
    legal_kind = "privacy"
    default_title = _("Privacy Policy")
    default_description = _(
        "How TECHWANDO collects, stores and protects member data, certificates "
        "and public athlete profile information."
    )


class TermsPageView(LegalPageMixin, TemplateView):
    template_name = "public/terms.html"
    page_slug = "terms-of-service"
    legal_kind = "terms"
    default_title = _("Terms of Use")
    default_description = _(
        "Terms of use, member code of conduct and acceptable use rules for the "
        "TECHWANDO club platform."
    )

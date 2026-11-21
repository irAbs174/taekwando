"""Public blog views and custom content-admin CRUD views."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.audit_logs.services import log_audit_event
from apps.blog.forms import CategoryBilingualForm, PostBilingualForm
from apps.blog.models import Category, Post, Tag
from apps.core.permissions import ContentAdminMixin
from apps.seo.models import RouteKey
from apps.seo.services import build_seo_context


class BlogListView(ListView):
    model = Post
    template_name = "public/blog_list.html"
    context_object_name = "posts"
    paginate_by = getattr(settings, "PUBLIC_PAGE_SIZE", 12)

    def get_queryset(self):
        qs = (
            Post.objects.published()
            .select_related("category", "author")
            .prefetch_related("translations", "category__translations", "tags")
            .order_by("-published_at", "-id")
        )
        cat_slug = (self.request.GET.get("category") or "").strip()
        tag_slug = (self.request.GET.get("tag") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        if tag_slug:
            qs = qs.filter(tags__slug=tag_slug)
        if q:
            qs = qs.filter(
                Q(translations__title__icontains=q)
                | Q(translations__excerpt__icontains=q)
                | Q(translations__body__icontains=q)
            ).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.filter(is_active=True).prefetch_related(
            "translations"
        )
        ctx["tags"] = Tag.objects.all()
        ctx["selected_category"] = (self.request.GET.get("category") or "").strip()
        ctx["selected_tag"] = (self.request.GET.get("tag") or "").strip()
        ctx["search_query"] = (self.request.GET.get("q") or "").strip()
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.BLOG,
                default_title=_("Martial Arts Blog & Technical Articles"),
                default_description=_(
                    "Articles on Taekwondo techniques, sports science, belt preparation, "
                    "and TEAKWONDO championship updates."
                ),
            )
        )
        return ctx


class BlogDetailView(DetailView):
    model = Post
    template_name = "public/blog_detail.html"
    context_object_name = "post"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Post.objects.published()
            .select_related("category", "author")
            .prefetch_related("translations", "category__translations", "tags")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        post: Post = self.object
        tr = post.get_translation(self.request.LANGUAGE_CODE)
        ctx["post_tr"] = tr
        ctx["related_posts"] = (
            Post.objects.published()
            .exclude(pk=post.pk)
            .prefetch_related("translations")
            .order_by("-published_at")[:3]
        )

        title = (tr.seo_title or tr.title) if tr else post.slug
        desc = (tr.seo_description or tr.excerpt or tr.body[:180]) if tr else ""
        img_url = post.featured_image.url if post.featured_image else ""
        structured = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": tr.title if tr else post.slug,
            "description": desc,
            "datePublished": post.published_at.isoformat() if post.published_at else post.created_at.isoformat(),
            "dateModified": post.updated_at.isoformat(),
            "inLanguage": tr.language if tr else self.request.LANGUAGE_CODE,
            "author": {
                "@type": "Organization",
                "name": settings.SITE_NAME,
            },
            "publisher": {
                "@type": "Organization",
                "name": settings.SITE_NAME,
            },
            "mainEntityOfPage": f"{settings.SITE_BASE_URL}{self.request.path}",
        }
        ctx.update(
            build_seo_context(
                self.request,
                default_title=title,
                default_description=desc,
                canonical_url=tr.canonical_url if tr else "",
                og_title=(tr.og_title or title) if tr else title,
                og_description=(tr.og_description or desc) if tr else desc,
                og_image_url=img_url,
                og_image_alt=tr.featured_image_alt if tr else title,
                og_type="article",
                robots_index=post.robots_index,
                robots_follow=post.robots_follow,
                structured_data=structured,
            )
        )
        return ctx


class AdminPostListView(ContentAdminMixin, ListView):
    model = Post
    template_name = "dashboard/admin/post_list.html"
    context_object_name = "posts"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            Post.objects.select_related("category", "author")
            .prefetch_related("translations", "category__translations")
            .order_by("-created_at")
        )
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs


class AdminPostCreateView(ContentAdminMixin, CreateView):
    model = Post
    form_class = PostBilingualForm
    template_name = "dashboard/admin/post_form.html"
    success_url = reverse_lazy("blog:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        form.instance.author = self.request.user
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="BLOG_POST_CREATED",
            instance=self.object,
            new_state={"status": self.object.status, "slug": self.object.slug},
            request=self.request,
        )
        messages.success(self.request, _("Blog article created successfully."))
        return resp


class AdminPostUpdateView(ContentAdminMixin, UpdateView):
    model = Post
    form_class = PostBilingualForm
    template_name = "dashboard/admin/post_form.html"
    success_url = reverse_lazy("blog:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="BLOG_POST_UPDATED",
            instance=self.object,
            new_state={"status": self.object.status, "slug": self.object.slug},
            request=self.request,
        )
        messages.success(self.request, _("Blog article updated successfully."))
        return resp


class AdminCategoryListView(ContentAdminMixin, ListView):
    model = Category
    template_name = "dashboard/admin/category_list.html"
    context_object_name = "categories"
    paginate_by = 25

    def get_queryset(self):
        return Category.objects.prefetch_related("translations")


class AdminCategoryCreateView(ContentAdminMixin, CreateView):
    model = Category
    form_class = CategoryBilingualForm
    template_name = "dashboard/admin/category_form.html"
    success_url = reverse_lazy("blog:admin_category_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="BLOG_CATEGORY_CREATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Blog category created."))
        return resp


class AdminCategoryUpdateView(ContentAdminMixin, UpdateView):
    model = Category
    form_class = CategoryBilingualForm
    template_name = "dashboard/admin/category_form.html"
    success_url = reverse_lazy("blog:admin_category_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="BLOG_CATEGORY_UPDATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Blog category updated."))
        return resp

"""Public product catalog views and custom content-admin CRUD views."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.audit_logs.services import log_audit_event
from apps.core.models import Discipline
from apps.core.permissions import ContentAdminMixin
from apps.products.forms import ProductBilingualForm, ProductCategoryBilingualForm
from apps.products.models import Product, ProductCategory
from apps.seo.models import RouteKey
from apps.seo.services import build_seo_context


class ProductListView(ListView):
    model = Product
    template_name = "public/product_list.html"
    context_object_name = "products"
    paginate_by = getattr(settings, "PUBLIC_PAGE_SIZE", 12)

    def get_queryset(self):
        qs = (
            Product.objects.published()
            .select_related("category")
            .prefetch_related("translations", "category__translations", "images")
        )
        cat_slug = (self.request.GET.get("category") or "").strip()
        discipline = (self.request.GET.get("discipline") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        if cat_slug:
            qs = qs.filter(category__slug=cat_slug)
        if discipline and discipline in dict(Discipline.choices):
            qs = qs.filter(discipline=discipline)
        if q:
            qs = qs.filter(
                Q(sku__icontains=q)
                | Q(translations__name__icontains=q)
                | Q(translations__short_description__icontains=q)
                | Q(translations__description__icontains=q)
            ).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = ProductCategory.objects.filter(is_active=True).prefetch_related(
            "translations"
        )
        ctx["disciplines"] = Discipline.choices
        ctx["selected_category"] = (self.request.GET.get("category") or "").strip()
        ctx["selected_discipline"] = (self.request.GET.get("discipline") or "").strip()
        ctx["search_query"] = (self.request.GET.get("q") or "").strip()
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.PRODUCTS,
                default_title=_("Martial Arts Equipment & Uniform Catalog"),
                default_description=_(
                    "Official TECHWANDO uniforms (Dobok & Dogi), certified protective gear, "
                    "belts, and training equipment."
                ),
            )
        )
        return ctx


class ProductDetailView(DetailView):
    model = Product
    template_name = "public/product_detail.html"
    context_object_name = "product"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return (
            Product.objects.published()
            .select_related("category")
            .prefetch_related("translations", "category__translations", "images")
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        product: Product = self.object
        tr = product.get_translation(self.request.LANGUAGE_CODE)
        ctx["product_tr"] = tr
        specs = []
        if tr and tr.specifications:
            specs = [line.strip() for line in tr.specifications.splitlines() if line.strip()]
        ctx["spec_lines"] = specs
        ctx["related_products"] = (
            Product.objects.published()
            .exclude(pk=product.pk)
            .prefetch_related("translations", "images")[:3]
        )

        title = (tr.seo_title or tr.name) if tr else product.slug
        desc = (tr.seo_description or tr.short_description or tr.description[:180]) if tr else ""
        primary = product.primary_image
        img_url = primary.image.url if primary else ""
        structured = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": tr.name if tr else product.slug,
            "sku": product.sku,
            "description": desc,
            "brand": {"@type": "Brand", "name": settings.SITE_NAME},
        }
        if product.price is not None:
            structured["offers"] = {
                "@type": "Offer",
                "price": str(product.price),
                "priceCurrency": product.currency or "JPY",
                "availability": (
                    "https://schema.org/InStock"
                    if product.is_available
                    else "https://schema.org/OutOfStock"
                ),
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
                og_image_alt=primary.localized_alt if primary else title,
                robots_index=product.robots_index,
                robots_follow=product.robots_follow,
                structured_data=structured,
            )
        )
        return ctx


class AdminProductListView(ContentAdminMixin, ListView):
    model = Product
    template_name = "dashboard/admin/product_list.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        return (
            Product.objects.select_related("category")
            .prefetch_related("translations", "category__translations", "images")
            .order_by("-created_at")
        )


class AdminProductCreateView(ContentAdminMixin, CreateView):
    model = Product
    form_class = ProductBilingualForm
    template_name = "dashboard/admin/product_form.html"
    success_url = reverse_lazy("products:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_related(self.object)
        log_audit_event(
            actor=self.request.user,
            action="PRODUCT_CREATED",
            instance=self.object,
            new_state={"sku": self.object.sku, "status": self.object.status},
            request=self.request,
        )
        messages.success(self.request, _("Product created successfully."))
        return resp


class AdminProductUpdateView(ContentAdminMixin, UpdateView):
    model = Product
    form_class = ProductBilingualForm
    template_name = "dashboard/admin/product_form.html"
    success_url = reverse_lazy("products:admin_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_related(self.object)
        log_audit_event(
            actor=self.request.user,
            action="PRODUCT_UPDATED",
            instance=self.object,
            new_state={"sku": self.object.sku, "status": self.object.status},
            request=self.request,
        )
        messages.success(self.request, _("Product updated successfully."))
        return resp


class AdminProductCategoryListView(ContentAdminMixin, ListView):
    model = ProductCategory
    template_name = "dashboard/admin/product_category_list.html"
    context_object_name = "categories"
    paginate_by = 25

    def get_queryset(self):
        return ProductCategory.objects.prefetch_related("translations")


class AdminProductCategoryCreateView(ContentAdminMixin, CreateView):
    model = ProductCategory
    form_class = ProductCategoryBilingualForm
    template_name = "dashboard/admin/product_category_form.html"
    success_url = reverse_lazy("products:admin_category_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="PRODUCT_CATEGORY_CREATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Product category created."))
        return resp


class AdminProductCategoryUpdateView(ContentAdminMixin, UpdateView):
    model = ProductCategory
    form_class = ProductCategoryBilingualForm
    template_name = "dashboard/admin/product_category_form.html"
    success_url = reverse_lazy("products:admin_category_list")

    @transaction.atomic
    def form_valid(self, form):
        resp = super().form_valid(form)
        form.save_translations(self.object)
        log_audit_event(
            actor=self.request.user,
            action="PRODUCT_CATEGORY_UPDATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Product category updated."))
        return resp

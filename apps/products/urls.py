"""Public product catalog and admin product management routes."""
from django.urls import path

from apps.products.views import (
    AdminProductCategoryCreateView,
    AdminProductCategoryListView,
    AdminProductCategoryUpdateView,
    AdminProductCreateView,
    AdminProductListView,
    AdminProductUpdateView,
    ProductDetailView,
    ProductListView,
)

app_name = "products"

urlpatterns = [
    path("", ProductListView.as_view(), name="list"),
    path("manage/", AdminProductListView.as_view(), name="admin_list"),
    path("manage/add/", AdminProductCreateView.as_view(), name="admin_add"),
    path("manage/<int:pk>/edit/", AdminProductUpdateView.as_view(), name="admin_edit"),
    path(
        "manage/categories/",
        AdminProductCategoryListView.as_view(),
        name="admin_category_list",
    ),
    path(
        "manage/categories/add/",
        AdminProductCategoryCreateView.as_view(),
        name="admin_category_add",
    ),
    path(
        "manage/categories/<int:pk>/edit/",
        AdminProductCategoryUpdateView.as_view(),
        name="admin_category_edit",
    ),
    path("<slug:slug>/", ProductDetailView.as_view(), name="detail"),
]

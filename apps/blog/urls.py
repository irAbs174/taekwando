"""Public blog and admin article/category routes."""
from django.urls import path

from apps.blog.views import (
    AdminCategoryCreateView,
    AdminCategoryListView,
    AdminCategoryUpdateView,
    AdminPostCreateView,
    AdminPostListView,
    AdminPostUpdateView,
    BlogDetailView,
    BlogListView,
)

app_name = "blog"

urlpatterns = [
    path("", BlogListView.as_view(), name="list"),
    path("manage/", AdminPostListView.as_view(), name="admin_list"),
    path("manage/add/", AdminPostCreateView.as_view(), name="admin_add"),
    path("manage/<int:pk>/edit/", AdminPostUpdateView.as_view(), name="admin_edit"),
    path("manage/categories/", AdminCategoryListView.as_view(), name="admin_category_list"),
    path(
        "manage/categories/add/",
        AdminCategoryCreateView.as_view(),
        name="admin_category_add",
    ),
    path(
        "manage/categories/<int:pk>/edit/",
        AdminCategoryUpdateView.as_view(),
        name="admin_category_edit",
    ),
    path("<slug:slug>/", BlogDetailView.as_view(), name="detail"),
]

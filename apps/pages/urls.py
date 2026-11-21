"""Public homepage, about, education, training programs, and admin page routes."""
from django.urls import path

from apps.pages.views import (
    AboutPageView,
    GalleryPageView,
    PrivacyPageView,
    TermsPageView,
    AdminPageCreateView,
    AdminPageListView,
    AdminPageUpdateView,
    EducationPageView,
    HomePageView,
    ServicesPageView,
    StaticPageDetailView,
)

app_name = "pages"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("about/", AboutPageView.as_view(), name="about"),
    path("education/", EducationPageView.as_view(), name="education"),
    path("services/", ServicesPageView.as_view(), name="services"),
    path("gallery/", GalleryPageView.as_view(), name="gallery"),
    path("privacy/", PrivacyPageView.as_view(), name="privacy"),
    path("terms/", TermsPageView.as_view(), name="terms"),
    path("pages/manage/", AdminPageListView.as_view(), name="admin_list"),
    path("pages/manage/add/", AdminPageCreateView.as_view(), name="admin_add"),
    path("pages/manage/<int:pk>/edit/", AdminPageUpdateView.as_view(), name="admin_edit"),
    path("pages/<slug:slug>/", StaticPageDetailView.as_view(), name="detail"),
]

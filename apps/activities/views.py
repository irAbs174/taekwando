"""Member CRUD and correction views for social activities."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.activities.forms import MemberSocialActivityForm
from apps.activities.models import SocialActivity
from apps.activities.services import ActivityService
from apps.audit_logs.services import log_audit_event
from apps.core.forms import CorrectionRequestForm
from apps.core.permissions import MemberRequiredMixin
from apps.core.services import ModerationService


class MemberActivityListView(MemberRequiredMixin, ListView):
    model = SocialActivity
    template_name = "dashboard/member/activity_list.html"
    context_object_name = "activities"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10)

    def get_queryset(self):
        qs = SocialActivity.objects.filter(member=self.member_profile).select_related(
            "reviewer"
        )
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(approval_status=status)
        return qs


class MemberActivityDetailView(MemberRequiredMixin, DetailView):
    model = SocialActivity
    template_name = "dashboard/member/activity_detail.html"
    context_object_name = "activity"

    def get_queryset(self):
        return SocialActivity.objects.filter(member=self.member_profile).select_related(
            "reviewer"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review_logs"] = ModerationService.get_logs_for_object(self.object)
        return ctx


class MemberActivityCreateView(MemberRequiredMixin, CreateView):
    model = SocialActivity
    form_class = MemberSocialActivityForm
    template_name = "dashboard/member/activity_form.html"

    def form_valid(self, form):
        ActivityService.submit_activity(
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Your social activity has been submitted and is pending moderation."),
        )
        return redirect("activities:member_list")


class MemberActivityUpdateView(MemberRequiredMixin, UpdateView):
    model = SocialActivity
    form_class = MemberSocialActivityForm
    template_name = "dashboard/member/activity_form.html"

    def get_queryset(self):
        return SocialActivity.objects.filter(member=self.member_profile)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_member_edit:
            raise PermissionDenied
        return obj

    def form_valid(self, form):
        ActivityService.update_activity(
            record=self.object,
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Social activity updated and resubmitted for moderation."),
        )
        return redirect("activities:member_detail", pk=self.object.pk)


class MemberActivityDeleteView(MemberRequiredMixin, View):
    template_name = "dashboard/member/confirm_delete.html"

    def _get_obj(self, pk: int) -> SocialActivity:
        obj = get_object_or_404(SocialActivity, pk=pk, member=self.member_profile)
        if not obj.can_member_delete:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "cancel_url": reverse("activities:member_list")},
        )

    def post(self, request, pk: int):
        obj = self._get_obj(pk)
        log_audit_event(
            actor=request.user,
            action="SUBMISSION_DELETED",
            instance=obj,
            request=request,
        )
        obj.delete()
        messages.success(request, _("Social activity removed."))
        return redirect("activities:member_list")


class MemberActivityCorrectionView(MemberRequiredMixin, View):
    template_name = "dashboard/member/request_correction.html"

    def _get_obj(self, pk: int) -> SocialActivity:
        obj = get_object_or_404(SocialActivity, pk=pk, member=self.member_profile)
        if not obj.can_request_correction:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "form": CorrectionRequestForm(), "cancel_url": obj.get_member_url()},
        )

    def post(self, request, pk: int):
        obj = self._get_obj(pk)
        form = CorrectionRequestForm(request.POST)
        if form.is_valid():
            ModerationService.request_correction(
                obj,
                actor=request.user,
                reason=form.cleaned_data["reason"],
                request=request,
            )
            messages.success(
                request,
                _("Correction request recorded. You can now edit and resubmit the activity."),
            )
            return redirect("activities:member_edit", pk=obj.pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "form": form, "cancel_url": obj.get_member_url()},
        )

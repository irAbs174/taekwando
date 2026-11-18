"""Member portal CRUD and correction-request views for medals."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.audit_logs.services import log_audit_event
from apps.core.forms import CorrectionRequestForm
from apps.core.permissions import MemberRequiredMixin
from apps.core.services import ModerationService
from apps.medals.forms import MemberMedalForm
from apps.medals.models import Medal
from apps.medals.services import MedalService


class MemberMedalListView(MemberRequiredMixin, ListView):
    model = Medal
    template_name = "dashboard/member/medal_list.html"
    context_object_name = "medals"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10)

    def get_queryset(self):
        qs = Medal.objects.filter(member=self.member_profile).select_related(
            "competition", "reviewer"
        )
        status = (self.request.GET.get("status") or "").strip()
        medal_type = (self.request.GET.get("medal_type") or "").strip()
        if status:
            qs = qs.filter(approval_status=status)
        if medal_type:
            qs = qs.filter(medal_type=medal_type)
        return qs


class MemberMedalDetailView(MemberRequiredMixin, DetailView):
    model = Medal
    template_name = "dashboard/member/medal_detail.html"
    context_object_name = "medal"

    def get_queryset(self):
        return Medal.objects.filter(member=self.member_profile).select_related(
            "competition", "reviewer"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review_logs"] = ModerationService.get_logs_for_object(self.object)
        return ctx


class MemberMedalCreateView(MemberRequiredMixin, CreateView):
    model = Medal
    form_class = MemberMedalForm
    template_name = "dashboard/member/medal_form.html"

    def form_valid(self, form):
        MedalService.submit_medal(
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Your medal submission has been recorded and is pending administrator review."),
        )
        return redirect("medals:member_list")


class MemberMedalUpdateView(MemberRequiredMixin, UpdateView):
    model = Medal
    form_class = MemberMedalForm
    template_name = "dashboard/member/medal_form.html"

    def get_queryset(self):
        return Medal.objects.filter(member=self.member_profile)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_member_edit:
            raise PermissionDenied
        return obj

    def form_valid(self, form):
        MedalService.update_medal(
            record=self.object,
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Medal submission updated and resubmitted for review."),
        )
        return redirect("medals:member_detail", pk=self.object.pk)


class MemberMedalDeleteView(MemberRequiredMixin, View):
    template_name = "dashboard/member/confirm_delete.html"

    def _get_obj(self, pk: int) -> Medal:
        obj = get_object_or_404(Medal, pk=pk, member=self.member_profile)
        if not obj.can_member_delete:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "cancel_url": reverse("medals:member_list")},
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
        messages.success(request, _("Medal submission deleted."))
        return redirect("medals:member_list")


class MemberMedalCorrectionView(MemberRequiredMixin, View):
    template_name = "dashboard/member/request_correction.html"

    def _get_obj(self, pk: int) -> Medal:
        obj = get_object_or_404(Medal, pk=pk, member=self.member_profile)
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
                _("Correction request recorded. You can now edit and resubmit the medal."),
            )
            return redirect("medals:member_edit", pk=obj.pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "form": form, "cancel_url": obj.get_member_url()},
        )

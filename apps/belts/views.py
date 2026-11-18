"""Views for member belt history CRUD, correction requests, and admin belt types."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.audit_logs.services import log_audit_event
from apps.belts.forms import BeltTypeAdminForm, MemberBeltPromotionForm
from apps.belts.models import BeltHistory, BeltType
from apps.belts.services import BeltService
from apps.core.forms import CorrectionRequestForm
from apps.core.permissions import ClubManagerMixin, MemberRequiredMixin
from apps.core.services import ModerationService


class MemberBeltListView(MemberRequiredMixin, ListView):
    model = BeltHistory
    template_name = "dashboard/member/belt_list.html"
    context_object_name = "belts"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10)

    def get_queryset(self):
        qs = BeltHistory.objects.filter(member=self.member_profile).select_related(
            "belt_type", "reviewer"
        )
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(approval_status=status)
        return qs


class MemberBeltDetailView(MemberRequiredMixin, DetailView):
    model = BeltHistory
    template_name = "dashboard/member/belt_detail.html"
    context_object_name = "belt"

    def get_queryset(self):
        return BeltHistory.objects.filter(member=self.member_profile).select_related(
            "belt_type", "reviewer"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review_logs"] = ModerationService.get_logs_for_object(self.object)
        return ctx


class MemberBeltCreateView(MemberRequiredMixin, CreateView):
    model = BeltHistory
    form_class = MemberBeltPromotionForm
    template_name = "dashboard/member/belt_form.html"

    def form_valid(self, form):
        BeltService.submit_belt_promotion(
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Your belt promotion request has been submitted and is pending review."),
        )
        return redirect("belts:member_list")


class MemberBeltUpdateView(MemberRequiredMixin, UpdateView):
    model = BeltHistory
    form_class = MemberBeltPromotionForm
    template_name = "dashboard/member/belt_form.html"

    def get_queryset(self):
        return BeltHistory.objects.filter(member=self.member_profile)

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        return response

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_member_edit:
            raise PermissionDenied
        return obj

    def form_valid(self, form):
        BeltService.update_belt_promotion(
            record=self.object,
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Belt promotion updated and resubmitted for administrator review."),
        )
        return redirect("belts:member_detail", pk=self.object.pk)


class MemberBeltDeleteView(MemberRequiredMixin, View):
    template_name = "dashboard/member/confirm_delete.html"

    def _get_obj(self, pk: int) -> BeltHistory:
        obj = get_object_or_404(BeltHistory, pk=pk, member=self.member_profile)
        if not obj.can_member_delete:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "cancel_url": reverse("belts:member_list")},
        )

    def post(self, request, pk: int):
        obj = self._get_obj(pk)
        log_audit_event(
            actor=request.user,
            action="SUBMISSION_DELETED",
            instance=obj,
            previous_state={"approval_status": obj.approval_status},
            request=request,
        )
        obj.delete()
        messages.success(request, _("Belt promotion submission removed."))
        return redirect("belts:member_list")


class MemberBeltCorrectionView(MemberRequiredMixin, View):
    template_name = "dashboard/member/request_correction.html"

    def _get_obj(self, pk: int) -> BeltHistory:
        obj = get_object_or_404(BeltHistory, pk=pk, member=self.member_profile)
        if not obj.can_request_correction:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {
                "object": obj,
                "form": CorrectionRequestForm(),
                "cancel_url": obj.get_member_url(),
            },
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
                _("Correction request recorded. You can now edit and resubmit the record."),
            )
            return redirect("belts:member_edit", pk=obj.pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "form": form, "cancel_url": obj.get_member_url()},
        )


class AdminBeltTypeListView(ClubManagerMixin, ListView):
    model = BeltType
    template_name = "dashboard/admin/belt_type_list.html"
    context_object_name = "belt_types"
    paginate_by = 25


class AdminBeltTypeCreateView(ClubManagerMixin, CreateView):
    model = BeltType
    form_class = BeltTypeAdminForm
    template_name = "dashboard/admin/belt_type_form.html"
    success_url = reverse_lazy("belts:admin_type_list")

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit_event(
            actor=self.request.user,
            action="BELT_TYPE_CREATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Belt rank created."))
        return resp


class AdminBeltTypeUpdateView(ClubManagerMixin, UpdateView):
    model = BeltType
    form_class = BeltTypeAdminForm
    template_name = "dashboard/admin/belt_type_form.html"
    success_url = reverse_lazy("belts:admin_type_list")

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit_event(
            actor=self.request.user,
            action="BELT_TYPE_UPDATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Belt rank updated."))
        return resp

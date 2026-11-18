"""Views for member competition participations and admin competition CRUD."""
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
from apps.competitions.forms import CompetitionAdminForm, MemberCompetitionParticipationForm
from apps.competitions.models import Competition, CompetitionParticipation
from apps.competitions.services import CompetitionService
from apps.core.forms import CorrectionRequestForm
from apps.core.permissions import ClubManagerMixin, MemberRequiredMixin
from apps.core.services import ModerationService


class MemberCompetitionListView(MemberRequiredMixin, ListView):
    model = CompetitionParticipation
    template_name = "dashboard/member/competition_list.html"
    context_object_name = "participations"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10)

    def get_queryset(self):
        qs = CompetitionParticipation.objects.filter(member=self.member_profile).select_related(
            "competition", "reviewer"
        )
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(approval_status=status)
        return qs


class MemberCompetitionDetailView(MemberRequiredMixin, DetailView):
    model = CompetitionParticipation
    template_name = "dashboard/member/competition_detail.html"
    context_object_name = "participation"

    def get_queryset(self):
        return CompetitionParticipation.objects.filter(member=self.member_profile).select_related(
            "competition", "reviewer"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review_logs"] = ModerationService.get_logs_for_object(self.object)
        return ctx


class MemberCompetitionCreateView(MemberRequiredMixin, CreateView):
    model = CompetitionParticipation
    form_class = MemberCompetitionParticipationForm
    template_name = "dashboard/member/competition_form.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["member"] = self.member_profile
        return kw

    def form_valid(self, form):
        CompetitionService.submit_participation(
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Competition participation submitted and awaiting review."),
        )
        return redirect("competitions:member_list")


class MemberCompetitionUpdateView(MemberRequiredMixin, UpdateView):
    model = CompetitionParticipation
    form_class = MemberCompetitionParticipationForm
    template_name = "dashboard/member/competition_form.html"

    def get_queryset(self):
        return CompetitionParticipation.objects.filter(member=self.member_profile)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_member_edit:
            raise PermissionDenied
        return obj

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["member"] = self.member_profile
        return kw

    def form_valid(self, form):
        CompetitionService.update_participation(
            record=self.object,
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(self.request, _("Competition record updated and resubmitted."))
        return redirect("competitions:member_detail", pk=self.object.pk)


class MemberCompetitionDeleteView(MemberRequiredMixin, View):
    template_name = "dashboard/member/confirm_delete.html"

    def _get_obj(self, pk: int) -> CompetitionParticipation:
        obj = get_object_or_404(CompetitionParticipation, pk=pk, member=self.member_profile)
        if not obj.can_member_delete:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "cancel_url": reverse("competitions:member_list")},
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
        messages.success(request, _("Competition participation deleted."))
        return redirect("competitions:member_list")


class MemberCompetitionCorrectionView(MemberRequiredMixin, View):
    template_name = "dashboard/member/request_correction.html"

    def _get_obj(self, pk: int) -> CompetitionParticipation:
        obj = get_object_or_404(CompetitionParticipation, pk=pk, member=self.member_profile)
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
                _("Correction request recorded. You can now edit and resubmit the record."),
            )
            return redirect("competitions:member_edit", pk=obj.pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "form": form, "cancel_url": obj.get_member_url()},
        )


class AdminCompetitionListView(ClubManagerMixin, ListView):
    model = Competition
    template_name = "dashboard/admin/competition_list.html"
    context_object_name = "competitions"
    paginate_by = 20


class AdminCompetitionCreateView(ClubManagerMixin, CreateView):
    model = Competition
    form_class = CompetitionAdminForm
    template_name = "dashboard/admin/competition_form.html"
    success_url = reverse_lazy("competitions:admin_list")

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit_event(
            actor=self.request.user,
            action="COMPETITION_CREATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Competition created."))
        return resp


class AdminCompetitionUpdateView(ClubManagerMixin, UpdateView):
    model = Competition
    form_class = CompetitionAdminForm
    template_name = "dashboard/admin/competition_form.html"
    success_url = reverse_lazy("competitions:admin_list")

    def form_valid(self, form):
        resp = super().form_valid(form)
        log_audit_event(
            actor=self.request.user,
            action="COMPETITION_UPDATED",
            instance=self.object,
            request=self.request,
        )
        messages.success(self.request, _("Competition updated."))
        return resp

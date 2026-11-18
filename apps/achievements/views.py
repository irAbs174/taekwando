"""Member CRUD and correction-request views for sports achievements."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.achievements.forms import MemberAchievementForm
from apps.achievements.models import Achievement
from apps.achievements.services import AchievementService
from apps.audit_logs.services import log_audit_event
from apps.core.forms import CorrectionRequestForm
from apps.core.permissions import MemberRequiredMixin
from apps.core.services import ModerationService


class MemberAchievementListView(MemberRequiredMixin, ListView):
    model = Achievement
    template_name = "dashboard/member/achievement_list.html"
    context_object_name = "achievements"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10)

    def get_queryset(self):
        qs = Achievement.objects.filter(member=self.member_profile).select_related(
            "competition", "reviewer"
        )
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(approval_status=status)
        return qs


class MemberAchievementDetailView(MemberRequiredMixin, DetailView):
    model = Achievement
    template_name = "dashboard/member/achievement_detail.html"
    context_object_name = "achievement"

    def get_queryset(self):
        return Achievement.objects.filter(member=self.member_profile).select_related(
            "competition", "reviewer"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["review_logs"] = ModerationService.get_logs_for_object(self.object)
        return ctx


class MemberAchievementCreateView(MemberRequiredMixin, CreateView):
    model = Achievement
    form_class = MemberAchievementForm
    template_name = "dashboard/member/achievement_form.html"

    def form_valid(self, form):
        AchievementService.submit_achievement(
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Your sports achievement has been submitted and is pending administrator review."),
        )
        return redirect("achievements:member_list")


class MemberAchievementUpdateView(MemberRequiredMixin, UpdateView):
    model = Achievement
    form_class = MemberAchievementForm
    template_name = "dashboard/member/achievement_form.html"

    def get_queryset(self):
        return Achievement.objects.filter(member=self.member_profile)

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if not obj.can_member_edit:
            raise PermissionDenied
        return obj

    def form_valid(self, form):
        AchievementService.update_achievement(
            record=self.object,
            member=self.member_profile,
            form=form,
            actor=self.request.user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Achievement updated and resubmitted for review."),
        )
        return redirect("achievements:member_detail", pk=self.object.pk)


class MemberAchievementDeleteView(MemberRequiredMixin, View):
    template_name = "dashboard/member/confirm_delete.html"

    def _get_obj(self, pk: int) -> Achievement:
        obj = get_object_or_404(Achievement, pk=pk, member=self.member_profile)
        if not obj.can_member_delete:
            raise PermissionDenied
        return obj

    def get(self, request, pk: int):
        obj = self._get_obj(pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "cancel_url": reverse("achievements:member_list")},
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
        messages.success(request, _("Achievement deleted."))
        return redirect("achievements:member_list")


class MemberAchievementCorrectionView(MemberRequiredMixin, View):
    template_name = "dashboard/member/request_correction.html"

    def _get_obj(self, pk: int) -> Achievement:
        obj = get_object_or_404(Achievement, pk=pk, member=self.member_profile)
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
                _("Correction request recorded. You can now edit and resubmit the achievement."),
            )
            return redirect("achievements:member_edit", pk=obj.pk)
        return render(
            request,
            self.template_name,
            {"object": obj, "form": form, "cancel_url": obj.get_member_url()},
        )

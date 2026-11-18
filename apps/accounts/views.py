"""Authentication, account settings, and custom Administration Dashboard views."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from apps.accounts.forms import (
    AccountSettingsForm,
    AdminCreateUserForm,
    EmailAuthenticationForm,
    MemberRegistrationForm,
    StyledPasswordChangeForm,
    StyledPasswordResetForm,
    StyledSetPasswordForm,
)
from apps.accounts.models import User, UserRole
from apps.accounts.services import AccountService
from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.audit_logs.models import AuditLog
from apps.audit_logs.services import log_audit_event
from apps.belts.models import BeltHistory
from apps.blog.models import Post
from apps.competitions.models import CompetitionParticipation
from apps.contact.models import ContactMessage
from apps.core.forms import ModerationDecisionForm
from apps.core.models import ApprovalStatus, ReviewLog
from apps.core.permissions import (
    AdminPortalMixin,
    ClubManagerMixin,
    ModeratorMixin,
    can_access_admin_portal,
    can_moderate_submission,
)
from apps.core.security import (
    clear_rate_limit,
    get_client_ip,
    is_rate_limited,
    record_rate_limit_hit,
    security_logger,
)
from apps.core.services import ModerationService
from apps.medals.models import Medal
from apps.members.forms import AdminMemberProfileForm, MembershipDecisionForm
from apps.members.models import MemberProfile, MembershipStatus
from apps.members.services import review_membership_application
from apps.products.models import Product


# =============================================================================
# Authentication & Member Account Views
# =============================================================================


class MemberRegisterView(FormView):
    template_name = "accounts/register.html"
    form_class = MemberRegistrationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:post_login_redirect")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = AccountService.register_public_member(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password1"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            phone=form.cleaned_data.get("phone", ""),
            primary_discipline=form.cleaned_data["primary_discipline"],
            preferred_language=self.request.LANGUAGE_CODE,
            request=self.request,
        )
        login(self.request, user)
        messages.success(
            self.request,
            _("Welcome to TECHWANDO! Your member account has been created."),
        )
        return redirect("members:dashboard")


class RateLimitedLoginView(FormView):
    """Email login view with IP + account rate limiting and security audit logging."""

    template_name = "accounts/login.html"
    form_class = EmailAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_active:
            return redirect("accounts:post_login_redirect")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["request"] = self.request
        return kw

    def _get_safe_redirect_url(self) -> str:
        next_url = self.request.POST.get("next") or self.request.GET.get("next") or ""
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return next_url
        return str(reverse_lazy("accounts:post_login_redirect"))

    def post(self, request, *args, **kwargs):
        ip = get_client_ip(request) or "unknown"
        raw_email = (request.POST.get("email") or "").strip().lower()
        max_attempts = getattr(settings, "LOGIN_RATE_LIMIT_ATTEMPTS", 5)
        window = getattr(settings, "LOGIN_RATE_LIMIT_WINDOW", 300)

        ip_blocked = is_rate_limited("login_ip", ip, max_attempts * 2, window)
        acct_blocked = bool(
            raw_email and is_rate_limited("login_acct", f"{ip}:{raw_email}", max_attempts, window)
        )
        if ip_blocked or acct_blocked:
            security_logger.warning("Rate-limited login attempt from ip=%s email=%s", ip, raw_email)
            form = self.get_form()
            form.errors.clear()
            form.add_error(
                None,
                _("Too many failed login attempts. Please wait a few minutes and try again."),
            )
            return render(request, self.template_name, {"form": form}, status=429)

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.get_user()
        ip = get_client_ip(self.request) or "unknown"
        clear_rate_limit("login_acct", f"{ip}:{user.email}")

        login(self.request, user)
        log_audit_event(
            actor=user,
            action="USER_LOGIN",
            instance=user,
            request=self.request,
        )
        messages.success(
            self.request,
            _("Welcome back, %(name)s.") % {"name": user.get_short_name()},
        )
        return redirect(self._get_safe_redirect_url())

    def form_invalid(self, form):
        ip = get_client_ip(self.request) or "unknown"
        raw_email = (self.request.POST.get("email") or "").strip().lower()
        window = getattr(settings, "LOGIN_RATE_LIMIT_WINDOW", 300)
        record_rate_limit_hit("login_ip", ip, window)
        if raw_email:
            record_rate_limit_hit("login_acct", f"{ip}:{raw_email}", window)
        security_logger.info("Failed login attempt from ip=%s email=%s", ip, raw_email)
        return super().form_invalid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["next"] = self.request.GET.get("next", "")
        return ctx


class SafeLogoutView(View):
    """CSRF-protected POST logout endpoint."""

    def post(self, request):
        if request.user.is_authenticated:
            log_audit_event(
                actor=request.user,
                action="USER_LOGOUT",
                instance=request.user,
                request=request,
            )
            logout(request)
            messages.info(request, _("You have been signed out safely."))
        return redirect("pages:home")


class PostLoginRedirectView(LoginRequiredMixin, View):
    """Route authenticated users to their appropriate dashboard."""

    def get(self, request):
        if can_access_admin_portal(request.user):
            return redirect("accounts:admin_dashboard")
        return redirect("members:dashboard")


class AccountSettingsView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = AccountSettingsForm
    template_name = "accounts/account_settings.html"
    success_url = reverse_lazy("members:account_settings")

    def get_object(self, queryset=None) -> User:
        return self.request.user

    def form_valid(self, form):
        old_email = User.objects.get(pk=self.request.user.pk).email
        resp = super().form_valid(form)
        if old_email != self.object.email:
            log_audit_event(
                actor=self.request.user,
                action="USER_EMAIL_UPDATED",
                instance=self.object,
                previous_state={"email": old_email},
                new_state={"email": self.object.email},
                request=self.request,
            )
        messages.success(self.request, _("Account settings updated."))
        return resp


class MemberPasswordChangeView(LoginRequiredMixin, FormView):
    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("members:account_settings")

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        log_audit_event(
            actor=user,
            action="USER_PASSWORD_CHANGED",
            instance=user,
            request=self.request,
        )
        messages.success(self.request, _("Your password has been changed successfully."))
        return super().form_valid(form)


class MemberPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "emails/password_reset_email.html"
    subject_template_name = "emails/password_reset_subject.txt"
    form_class = StyledPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")


class MemberPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class MemberPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = StyledSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")


class MemberPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


# =============================================================================
# Custom Administration Dashboard & Moderation Center
# =============================================================================

MODERATED_MODEL_MAP = {
    "medal": (Medal, _("Medal")),
    "achievement": (Achievement, _("Achievement")),
    "belthistory": (BeltHistory, _("Belt Promotion")),
    "socialactivity": (SocialActivity, _("Social Activity")),
    "competitionparticipation": (CompetitionParticipation, _("Competition Record")),
}


class AdminDashboardView(AdminPortalMixin, TemplateView):
    template_name = "dashboard/admin/overview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["counts"] = {
            "total_members": MemberProfile.objects.count(),
            "pending_memberships": MemberProfile.objects.filter(
                membership_status=MembershipStatus.PENDING
            ).count(),
            "pending_medals": Medal.objects.filter(
                approval_status=ApprovalStatus.PENDING
            ).count(),
            "pending_achievements": Achievement.objects.filter(
                approval_status=ApprovalStatus.PENDING
            ).count(),
            "pending_belts": BeltHistory.objects.filter(
                approval_status=ApprovalStatus.PENDING
            ).count(),
            "pending_activities": SocialActivity.objects.filter(
                approval_status=ApprovalStatus.PENDING
            ).count(),
            "pending_competitions": CompetitionParticipation.objects.filter(
                approval_status=ApprovalStatus.PENDING
            ).count(),
            "unread_contacts": ContactMessage.objects.filter(is_read=False).count(),
            "blog_posts": Post.objects.count(),
            "products": Product.objects.count(),
        }
        ctx["counts"]["total_pending_submissions"] = (
            ctx["counts"]["pending_medals"]
            + ctx["counts"]["pending_achievements"]
            + ctx["counts"]["pending_belts"]
            + ctx["counts"]["pending_activities"]
            + ctx["counts"]["pending_competitions"]
        )
        ctx["recent_reviews"] = ReviewLog.objects.select_related("reviewer")[:8]
        ctx["recent_audits"] = AuditLog.objects.select_related("actor")[:8]
        return ctx


class ModerationQueueView(ModeratorMixin, TemplateView):
    template_name = "dashboard/admin/moderation_queue.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        status_filter = (self.request.GET.get("status") or ApprovalStatus.PENDING).strip()
        type_filter = (self.request.GET.get("type") or "all").strip()

        valid_statuses = {c for c, _ in ApprovalStatus.choices} | {"ALL"}
        if status_filter not in valid_statuses:
            status_filter = ApprovalStatus.PENDING

        queue_items = []
        for key, (model_cls, label) in MODERATED_MODEL_MAP.items():
            if type_filter != "all" and type_filter != key:
                continue
            if not can_moderate_submission(self.request.user, key):
                continue
            qs = model_cls.objects.select_related("member", "member__user", "reviewer")
            if status_filter != "ALL":
                qs = qs.filter(approval_status=status_filter)
            for item in qs.order_by("-updated_at")[:50]:
                queue_items.append(
                    {
                        "model_type": key,
                        "type_label": label,
                        "pk": item.pk,
                        "title": str(item),
                        "member": item.member,
                        "status": item.approval_status,
                        "correction_request": item.correction_request,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at,
                        "reviewer": item.reviewer,
                    }
                )

        queue_items.sort(key=lambda x: x["updated_at"], reverse=True)
        ctx.update(
            {
                "queue_items": queue_items[:80],
                "status_filter": status_filter,
                "type_filter": type_filter,
                "status_choices": ApprovalStatus.choices,
                "type_choices": [(k, v[1]) for k, v in MODERATED_MODEL_MAP.items()],
            }
        )
        return ctx


class ReviewSubmissionView(ModeratorMixin, View):
    template_name = "dashboard/admin/review_submission.html"

    def _resolve_submission(self, request, model_type: str, pk: int):
        entry = MODERATED_MODEL_MAP.get(model_type)
        if not entry:
            raise Http404
        model_cls, label = entry
        if not can_moderate_submission(request.user, model_type):
            raise PermissionDenied
        obj = get_object_or_404(
            model_cls.objects.select_related("member", "member__user", "reviewer"),
            pk=pk,
        )
        return obj, label

    def _file_url_for(self, model_type: str, obj) -> str:
        if model_type == "medal":
            return obj.get_evidence_url()
        if model_type in {"achievement", "belthistory", "competitionparticipation"}:
            return obj.get_certificate_url()
        if model_type == "socialactivity":
            return obj.get_private_photo_url()
        return ""

    def get(self, request, model_type: str, pk: int):
        obj, label = self._resolve_submission(request, model_type, pk)
        form = ModerationDecisionForm(
            initial={
                "approval_status": (
                    obj.approval_status
                    if obj.approval_status != ApprovalStatus.PENDING
                    else ApprovalStatus.APPROVED
                ),
                "admin_note": obj.admin_note,
            }
        )
        return render(
            request,
            self.template_name,
            {
                "submission": obj,
                "model_type": model_type,
                "type_label": label,
                "evidence_url": self._file_url_for(model_type, obj),
                "form": form,
                "review_logs": ModerationService.get_logs_for_object(obj),
            },
        )

    def post(self, request, model_type: str, pk: int):
        obj, label = self._resolve_submission(request, model_type, pk)
        form = ModerationDecisionForm(request.POST)
        if form.is_valid():
            ModerationService.review_submission(
                obj,
                reviewer=request.user,
                new_status=form.cleaned_data["approval_status"],
                note=form.cleaned_data["admin_note"],
                request=request,
            )
            messages.success(
                request,
                _("Moderation decision saved and the member has been notified."),
            )
            return redirect("accounts:admin_moderation_queue")
        return render(
            request,
            self.template_name,
            {
                "submission": obj,
                "model_type": model_type,
                "type_label": label,
                "evidence_url": self._file_url_for(model_type, obj),
                "form": form,
                "review_logs": ModerationService.get_logs_for_object(obj),
            },
        )


class AdminMemberListView(ClubManagerMixin, ListView):
    model = MemberProfile
    template_name = "dashboard/admin/member_list.html"
    context_object_name = "members"
    paginate_by = 20

    def get_queryset(self):
        qs = MemberProfile.objects.select_related("user").order_by("-joining_date", "-id")
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        if status in dict(MembershipStatus.choices):
            qs = qs.filter(membership_status=status)
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(first_name_ja__icontains=q)
                | Q(last_name_ja__icontains=q)
                | Q(membership_number__icontains=q)
                | Q(user__email__icontains=q)
            )
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = MembershipStatus.choices
        ctx["status_filter"] = (self.request.GET.get("status") or "").strip()
        ctx["search_query"] = (self.request.GET.get("q") or "").strip()
        return ctx


class AdminMemberCreateView(ClubManagerMixin, FormView):
    template_name = "dashboard/admin/member_form.html"
    form_class = AdminCreateUserForm

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["actor"] = self.request.user
        return kw

    def form_valid(self, form):
        user = AccountService.create_user_by_admin(
            actor=self.request.user,
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
            role=form.cleaned_data["role"],
            phone=form.cleaned_data.get("phone", ""),
            primary_discipline=form.cleaned_data["primary_discipline"],
            approve_immediately=form.cleaned_data["approve_immediately"],
            request=self.request,
        )
        messages.success(self.request, _("Member account created successfully."))
        return redirect("accounts:admin_member_detail", pk=user.member_profile.pk)


class AdminMemberDetailView(ClubManagerMixin, View):
    template_name = "dashboard/admin/member_detail.html"

    def get(self, request, pk: int):
        profile = get_object_or_404(
            MemberProfile.objects.select_related("user", "reviewer"), pk=pk
        )
        decision_form = MembershipDecisionForm(
            initial={
                "membership_status": profile.membership_status,
                "admin_note": profile.admin_note,
            }
        )
        profile_form = AdminMemberProfileForm(instance=profile)
        return render(
            request,
            self.template_name,
            {
                "member": profile,
                "decision_form": decision_form,
                "profile_form": profile_form,
                "roles": UserRole.choices,
                "can_change_role": request.user.is_superuser
                or request.user.role == UserRole.SUPER_ADMIN,
                "medals": profile.medals.all()[:10],
                "achievements": profile.achievements.all()[:10],
                "belts": profile.belt_histories.select_related("belt_type").all()[:10],
                "activities": profile.social_activities.all()[:10],
                "review_logs": ModerationService.get_logs_for_object(profile),
            },
        )

    def post(self, request, pk: int):
        profile = get_object_or_404(
            MemberProfile.objects.select_related("user", "reviewer"), pk=pk
        )
        action = request.POST.get("action")

        if action == "review_membership":
            form = MembershipDecisionForm(request.POST)
            if form.is_valid():
                review_membership_application(
                    profile=profile,
                    reviewer=request.user,
                    new_status=form.cleaned_data["membership_status"],
                    note=form.cleaned_data["admin_note"],
                    request=request,
                )
                messages.success(request, _("Membership status updated."))
            return redirect("accounts:admin_member_detail", pk=profile.pk)

        if action == "toggle_active":
            try:
                AccountService.set_user_active_status(
                    actor=request.user,
                    target_user=profile.user,
                    is_active=not profile.user.is_active,
                    request=request,
                )
                messages.success(request, _("Account active status updated."))
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("accounts:admin_member_detail", pk=profile.pk)

        if action == "change_role":
            new_role = (request.POST.get("role") or "").strip()
            try:
                AccountService.change_user_role(
                    actor=request.user,
                    target_user=profile.user,
                    new_role=new_role,
                    request=request,
                )
                messages.success(request, _("User role updated."))
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("accounts:admin_member_detail", pk=profile.pk)

        if action == "edit_profile":
            old_status = profile.membership_status
            pform = AdminMemberProfileForm(request.POST, request.FILES, instance=profile)
            if pform.is_valid():
                updated = pform.save(commit=False)
                desired_status = updated.membership_status
                desired_note = updated.admin_note
                updated.membership_status = old_status
                updated.save()
                if desired_status != old_status:
                    review_membership_application(
                        profile=updated,
                        reviewer=request.user,
                        new_status=desired_status,
                        note=desired_note,
                        request=request,
                    )
                else:
                    log_audit_event(
                        actor=request.user,
                        action="ADMIN_UPDATED_MEMBER_PROFILE",
                        instance=updated,
                        request=request,
                    )
                messages.success(request, _("Member profile updated."))
                return redirect("accounts:admin_member_detail", pk=profile.pk)
            messages.error(request, _("Please correct the highlighted profile fields."))

        return redirect("accounts:admin_member_detail", pk=profile.pk)

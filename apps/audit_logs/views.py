"""Administrative views for audit logs and moderation review history."""
from django.conf import settings
from django.db.models import Q
from django.views.generic import ListView

from apps.audit_logs.forms import AuditLogFilterForm
from apps.audit_logs.models import AuditLog
from apps.core.models import ReviewLog
from apps.core.permissions import ClubManagerMixin, ModeratorMixin


class AuditLogListView(ClubManagerMixin, ListView):
    model = AuditLog
    template_name = "dashboard/admin/audit_log_list.html"
    context_object_name = "logs"
    paginate_by = 25

    def get_queryset(self):
        qs = AuditLog.objects.select_related("actor").order_by("-created_at", "-id")
        q = (self.request.GET.get("q") or "").strip()
        action = (self.request.GET.get("action") or "").strip()
        target_model = (self.request.GET.get("target_model") or "").strip()
        if q:
            qs = qs.filter(
                Q(actor_email__icontains=q)
                | Q(action__icontains=q)
                | Q(target_model__icontains=q)
                | Q(target_repr__icontains=q)
                | Q(ip_address__icontains=q)
            )
        if action:
            qs = qs.filter(action__iexact=action)
        if target_model:
            qs = qs.filter(target_model__icontains=target_model)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = AuditLogFilterForm(self.request.GET or None)
        ctx["distinct_actions"] = (
            AuditLog.objects.values_list("action", flat=True).distinct().order_by("action")
        )
        return ctx


class ReviewLogListView(ModeratorMixin, ListView):
    model = ReviewLog
    template_name = "dashboard/admin/review_log_list.html"
    context_object_name = "review_logs"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10) * 2

    def get_queryset(self):
        qs = ReviewLog.objects.select_related("reviewer", "content_type").order_by(
            "-created_at", "-id"
        )
        status = (self.request.GET.get("status") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        if status:
            qs = qs.filter(new_status=status)
        if q:
            qs = qs.filter(
                Q(target_repr__icontains=q)
                | Q(note__icontains=q)
                | Q(reviewer__email__icontains=q)
            )
        return qs

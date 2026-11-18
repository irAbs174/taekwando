"""Views for the authenticated user's notification center."""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import translate_url
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import get_language
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import ListView

from apps.notifications.models import Notification
from apps.notifications.services import NotificationService


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "dashboard/member/notification_list.html"
    context_object_name = "notifications"
    paginate_by = getattr(settings, "DASHBOARD_PAGE_SIZE", 10)

    def get_queryset(self):
        # Strictly scoped to the logged-in user
        qs = Notification.objects.filter(recipient=self.request.user)
        if self.request.GET.get("filter") == "unread":
            qs = qs.filter(is_read=False)
        return qs


class NotificationMarkReadView(LoginRequiredMixin, View):
    def post(self, request, pk: int):
        notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
        NotificationService.mark_as_read(notif, request.user)
        if request.POST.get("go") == "1" and notif.target_url:
            target = notif.target_url
            if url_has_allowed_host_and_scheme(
                url=target,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                lang = get_language() or "fa"
                return redirect(translate_url(target, lang))
        return redirect("notifications:list")


class NotificationMarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        count = NotificationService.mark_all_as_read(request.user)
        if count:
            messages.success(request, _("All notifications marked as read."))
        return redirect("notifications:list")

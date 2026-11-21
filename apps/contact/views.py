"""Public contact page and admin contact message management views."""
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import FormView, ListView

from apps.contact.forms import ContactAdminNoteForm, PublicContactForm
from apps.contact.models import ContactMessage
from apps.contact.services import ContactService
from apps.core.permissions import AdminPortalMixin
from apps.seo.models import RouteKey
from apps.seo.services import build_seo_context


class PublicContactView(FormView):
    template_name = "public/contact.html"
    form_class = PublicContactForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.CONTACT,
                default_title=_("Contact TECHWANDO Club"),
                default_description=_(
                    "Reach out to TECHWANDO martial arts academy regarding classes, "
                    "membership, competitions, and training equipment."
                ),
            )
        )
        return ctx

    def form_valid(self, form):
        try:
            ContactService.submit_message(
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                subject=form.cleaned_data["subject"],
                message=form.cleaned_data["message"],
                language=self.request.LANGUAGE_CODE,
                request=self.request,
            )
        except ValidationError as exc:
            form.add_error(None, exc.message)
            return self.form_invalid(form)

        messages.success(
            self.request,
            _("Thank you! Your message has been sent to the TECHWANDO club team."),
        )
        return redirect("contact:public")


class AdminContactListView(AdminPortalMixin, ListView):
    model = ContactMessage
    template_name = "dashboard/admin/contact_list.html"
    context_object_name = "contact_messages"
    paginate_by = 20

    def get_queryset(self):
        qs = ContactMessage.objects.select_related("handled_by")
        status = self.request.GET.get("status")
        lang = self.request.GET.get("lang")
        q = (self.request.GET.get("q") or "").strip()
        if status == "unread":
            qs = qs.filter(is_read=False)
        elif status == "read":
            qs = qs.filter(is_read=True)
        if lang in {"fa", "ko"}:
            qs = qs.filter(language=lang)
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(subject__icontains=q)
                | Q(message__icontains=q)
            )
        return qs


class AdminContactDetailView(AdminPortalMixin, View):
    template_name = "dashboard/admin/contact_detail.html"

    def get(self, request, pk: int):
        msg = get_object_or_404(ContactMessage, pk=pk)
        if not msg.is_read:
            ContactService.mark_reviewed(
                msg, actor=request.user, is_read=True, request=request
            )
        form = ContactAdminNoteForm(
            initial={"is_read": msg.is_read, "internal_note": msg.internal_note}
        )
        return render(request, self.template_name, {"contact_message": msg, "form": form})

    def post(self, request, pk: int):
        msg = get_object_or_404(ContactMessage, pk=pk)
        form = ContactAdminNoteForm(request.POST)
        if form.is_valid():
            ContactService.mark_reviewed(
                msg,
                actor=request.user,
                is_read=form.cleaned_data["is_read"],
                internal_note=form.cleaned_data["internal_note"],
                request=request,
            )
            messages.success(request, _("Contact message updated."))
            return redirect("contact:admin_detail", pk=msg.pk)
        return render(request, self.template_name, {"contact_message": msg, "form": form})

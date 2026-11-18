"""Views for the private Member Portal and the public Champions & Medal Winners pages."""
from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, DateField, Max, Q
from django.db.models.functions import Coalesce, Greatest
from django.shortcuts import redirect
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from apps.achievements.models import Achievement
from apps.activities.models import SocialActivity
from apps.audit_logs.services import log_audit_event
from apps.belts.models import BeltHistory, BeltType
from apps.competitions.models import Competition, CompetitionParticipation
from apps.core.models import ApprovalStatus, Discipline
from apps.core.permissions import MemberRequiredMixin
from apps.medals.models import Medal, MedalType
from apps.members.forms import MemberProfileEditForm
from apps.members.models import MemberProfile
from apps.seo.models import RouteKey
from apps.seo.services import build_seo_context


# =============================================================================
# Private Club Member Portal Views
# =============================================================================


class MemberDashboardView(MemberRequiredMixin, TemplateView):
    template_name = "dashboard/member/overview.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        profile = self.member_profile

        medal_qs = Medal.objects.filter(member=profile)
        achievement_qs = Achievement.objects.filter(member=profile)
        belt_qs = BeltHistory.objects.filter(member=profile)
        comp_qs = CompetitionParticipation.objects.filter(member=profile)
        activity_qs = SocialActivity.objects.filter(member=profile)

        approved_medals = medal_qs.filter(approval_status=ApprovalStatus.APPROVED)
        medal_breakdown = {
            "total": approved_medals.count(),
            "gold": approved_medals.filter(medal_type=MedalType.GOLD).count(),
            "silver": approved_medals.filter(medal_type=MedalType.SILVER).count(),
            "bronze": approved_medals.filter(medal_type=MedalType.BRONZE).count(),
            "other": approved_medals.filter(medal_type=MedalType.OTHER).count(),
        }

        pending_statuses = [ApprovalStatus.PENDING, ApprovalStatus.NEEDS_REVISION]
        pending_count = (
            medal_qs.filter(approval_status__in=pending_statuses).count()
            + achievement_qs.filter(approval_status__in=pending_statuses).count()
            + belt_qs.filter(approval_status__in=pending_statuses).count()
            + comp_qs.filter(approval_status__in=pending_statuses).count()
            + activity_qs.filter(approval_status__in=pending_statuses).count()
        )

        # Combine recent submissions across domains for unified timeline
        recent_items = []
        for m in medal_qs.order_by("-created_at")[:4]:
            recent_items.append(
                {
                    "kind": _("Medal"),
                    "title": str(m),
                    "date": m.award_date,
                    "created_at": m.created_at,
                    "status": m.approval_status,
                    "note": m.admin_note,
                    "url": m.get_member_url(),
                }
            )
        for a in achievement_qs.order_by("-created_at")[:4]:
            recent_items.append(
                {
                    "kind": _("Achievement"),
                    "title": a.localized_title,
                    "date": a.achievement_date,
                    "created_at": a.created_at,
                    "status": a.approval_status,
                    "note": a.admin_note,
                    "url": a.get_member_url(),
                }
            )
        for b in belt_qs.select_related("belt_type").order_by("-created_at")[:4]:
            recent_items.append(
                {
                    "kind": _("Belt Promotion"),
                    "title": b.belt_type.localized_name,
                    "date": b.award_date,
                    "created_at": b.created_at,
                    "status": b.approval_status,
                    "note": b.admin_note,
                    "url": b.get_member_url(),
                }
            )
        for s in activity_qs.order_by("-created_at")[:4]:
            recent_items.append(
                {
                    "kind": _("Social Activity"),
                    "title": s.localized_title,
                    "date": s.activity_date,
                    "created_at": s.created_at,
                    "status": s.approval_status,
                    "note": s.admin_note,
                    "url": s.get_member_url(),
                }
            )
        recent_items.sort(key=lambda item: item["created_at"], reverse=True)

        ctx.update(
            {
                "profile": profile,
                "current_belt": profile.current_approved_belt,
                "medal_breakdown": medal_breakdown,
                "approved_achievements_count": achievement_qs.filter(
                    approval_status=ApprovalStatus.APPROVED
                ).count(),
                "approved_competitions_count": comp_qs.filter(
                    approval_status=ApprovalStatus.APPROVED
                ).count(),
                "pending_submissions_count": pending_count,
                "recent_items": recent_items[:8],
                "recent_activities": activity_qs.order_by("-activity_date")[:4],
            }
        )
        return ctx


class MemberProfileEditView(MemberRequiredMixin, UpdateView):
    """Edit the currently logged-in member's own profile (never accepts other IDs)."""

    model = MemberProfile
    form_class = MemberProfileEditForm
    template_name = "dashboard/member/profile_edit.html"
    context_object_name = "profile"

    def get_object(self, queryset=None) -> MemberProfile:
        return self.member_profile

    def form_valid(self, form):
        changed = list(form.changed_data)
        form.save()
        if changed:
            log_audit_event(
                actor=self.request.user,
                action="MEMBER_PROFILE_UPDATED",
                instance=self.member_profile,
                new_state={
                    "changed_fields": changed,
                    "public_profile_consent": self.member_profile.public_profile_consent,
                    "public_profile_visibility": self.member_profile.public_profile_visibility,
                },
                request=self.request,
            )
        messages.success(self.request, _("Your profile has been updated."))
        return redirect("members:profile_edit")


# =============================================================================
# Public Champions, Medal Winners, Belt Achievements & Competition Results
# =============================================================================


class PublicChampionsListView(ListView):
    model = MemberProfile
    template_name = "public/champions_list.html"
    context_object_name = "athletes"
    paginate_by = getattr(settings, "PUBLIC_PAGE_SIZE", 12)

    def get_queryset(self):
        qs = MemberProfile.objects.publicly_visible().annotate(
            approved_medal_count=Count(
                "medals",
                filter=Q(medals__approval_status=ApprovalStatus.APPROVED),
                distinct=True,
            ),
            gold_count=Count(
                "medals",
                filter=Q(
                    medals__approval_status=ApprovalStatus.APPROVED,
                    medals__medal_type=MedalType.GOLD,
                ),
                distinct=True,
            ),
            silver_count=Count(
                "medals",
                filter=Q(
                    medals__approval_status=ApprovalStatus.APPROVED,
                    medals__medal_type=MedalType.SILVER,
                ),
                distinct=True,
            ),
            bronze_count=Count(
                "medals",
                filter=Q(
                    medals__approval_status=ApprovalStatus.APPROVED,
                    medals__medal_type=MedalType.BRONZE,
                ),
                distinct=True,
            ),
            approved_achievement_count=Count(
                "achievements",
                filter=Q(achievements__approval_status=ApprovalStatus.APPROVED),
                distinct=True,
            ),
            latest_ach_date=Max(
                "achievements__achievement_date",
                filter=Q(achievements__approval_status=ApprovalStatus.APPROVED),
            ),
            latest_medal_date=Max(
                "medals__award_date",
                filter=Q(medals__approval_status=ApprovalStatus.APPROVED),
            ),
        ).annotate(
            latest_record_date=Greatest(
                Coalesce("latest_ach_date", "joining_date", output_field=DateField()),
                Coalesce("latest_medal_date", "joining_date", output_field=DateField()),
            )
        )

        q = (self.request.GET.get("q") or "").strip()
        discipline = (self.request.GET.get("discipline") or "").strip()
        belt_id = (self.request.GET.get("belt") or "").strip()
        competition_id = (self.request.GET.get("competition") or "").strip()
        medal_type = (self.request.GET.get("medal_type") or "").strip()
        sort = (self.request.GET.get("sort") or "-latest_achievement").strip()

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(first_name_ja__icontains=q)
                | Q(last_name_ja__icontains=q)
            )
        if discipline in dict(Discipline.choices):
            qs = qs.filter(
                Q(primary_discipline=discipline)
                | Q(
                    medals__approval_status=ApprovalStatus.APPROVED,
                    medals__discipline=discipline,
                )
                | Q(
                    achievements__approval_status=ApprovalStatus.APPROVED,
                    achievements__discipline=discipline,
                )
                | Q(
                    belt_histories__approval_status=ApprovalStatus.APPROVED,
                    belt_histories__discipline=discipline,
                )
            )
        if belt_id.isdigit():
            qs = qs.filter(
                belt_histories__approval_status=ApprovalStatus.APPROVED,
                belt_histories__belt_type_id=int(belt_id),
            )
        if competition_id.isdigit():
            cid = int(competition_id)
            qs = qs.filter(
                Q(
                    medals__approval_status=ApprovalStatus.APPROVED,
                    medals__competition_id=cid,
                )
                | Q(
                    achievements__approval_status=ApprovalStatus.APPROVED,
                    achievements__competition_id=cid,
                )
                | Q(
                    competition_participations__approval_status=ApprovalStatus.APPROVED,
                    competition_participations__competition_id=cid,
                )
            )
        if medal_type in dict(MedalType.choices):
            qs = qs.filter(
                medals__approval_status=ApprovalStatus.APPROVED,
                medals__medal_type=medal_type,
            )

        qs = qs.distinct()

        sort_map = {
            "-latest_achievement": ("-latest_record_date", "-approved_medal_count", "last_name"),
            "latest_achievement": ("latest_record_date", "last_name"),
            "-medal_count": ("-approved_medal_count", "-gold_count", "last_name"),
            "name": ("last_name", "first_name"),
        }
        return qs.order_by(*sort_map.get(sort, sort_map["-latest_achievement"]))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "disciplines": Discipline.choices,
                "belt_types": BeltType.objects.filter(is_active=True).order_by(
                    "discipline", "-rank_order"
                ),
                "competitions": Competition.objects.filter(is_published=True).order_by(
                    "-start_date"
                ),
                "medal_types": MedalType.choices,
                "filters": {
                    "q": (self.request.GET.get("q") or "").strip(),
                    "discipline": (self.request.GET.get("discipline") or "").strip(),
                    "belt": (self.request.GET.get("belt") or "").strip(),
                    "competition": (self.request.GET.get("competition") or "").strip(),
                    "medal_type": (self.request.GET.get("medal_type") or "").strip(),
                    "sort": (self.request.GET.get("sort") or "-latest_achievement").strip(),
                },
            }
        )
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.CHAMPIONS,
                default_title=_("TECHWANDO Champions & Verified Athletes"),
                default_description=_(
                    "Official directory of approved TECHWANDO martial arts athletes, "
                    "medal winners, black belt holders, and championship records."
                ),
            )
        )
        return ctx


class PublicChampionDetailView(DetailView):
    """
    Public verified athlete profile page.
    Strictly filters to approved, publicly-consented, publicly-visible members and
    exposes ONLY approved sports records. Private data (email, phone, birth_date,
    certificates, evidence files, review notes) is NEVER passed or rendered.
    """

    model = MemberProfile
    template_name = "public/champion_detail.html"
    context_object_name = "athlete"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return MemberProfile.objects.publicly_visible()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        athlete: MemberProfile = self.object

        approved_medals = (
            athlete.medals.filter(approval_status=ApprovalStatus.APPROVED)
            .select_related("competition")
            .order_by("-award_date", "-id")
        )
        approved_achievements = (
            athlete.achievements.filter(approval_status=ApprovalStatus.APPROVED)
            .select_related("competition")
            .order_by("-achievement_date", "-id")
        )
        approved_belts = (
            athlete.belt_histories.filter(approval_status=ApprovalStatus.APPROVED)
            .select_related("belt_type")
            .order_by("-belt_type__rank_order", "-award_date")
        )
        approved_competitions = (
            athlete.competition_participations.filter(
                approval_status=ApprovalStatus.APPROVED,
                competition__is_published=True,
            )
            .select_related("competition")
            .order_by("-competition__start_date")
        )
        approved_public_activities = athlete.social_activities.filter(
            approval_status=ApprovalStatus.APPROVED,
            public_visibility_consent=True,
        ).order_by("-activity_date")

        medal_summary = {
            "total": approved_medals.count(),
            "gold": approved_medals.filter(medal_type=MedalType.GOLD).count(),
            "silver": approved_medals.filter(medal_type=MedalType.SILVER).count(),
            "bronze": approved_medals.filter(medal_type=MedalType.BRONZE).count(),
            "other": approved_medals.filter(medal_type=MedalType.OTHER).count(),
        }

        ctx.update(
            {
                "current_belt": approved_belts.first(),
                "approved_medals": approved_medals,
                "approved_achievements": approved_achievements,
                "approved_belts": approved_belts,
                "approved_competitions": approved_competitions,
                "approved_activities": approved_public_activities,
                "medal_summary": medal_summary,
            }
        )

        structured = {
            "@context": "https://schema.org",
            "@type": "Person",
            "name": athlete.localized_full_name,
            "description": athlete.localized_biography[:240] if athlete.localized_biography else "",
            "memberOf": {
                "@type": "SportsClub",
                "name": settings.SITE_NAME,
            },
            "url": f"{settings.SITE_BASE_URL}{self.request.path}",
        }
        ctx.update(
            build_seo_context(
                self.request,
                default_title=f"{athlete.localized_full_name} — {_('Champion Profile')}",
                default_description=(
                    athlete.localized_biography[:200]
                    if athlete.localized_biography
                    else _("Verified athlete profile at TECHWANDO Club.")
                ),
                og_image_url=athlete.profile_photo.url if athlete.profile_photo else "",
                og_image_alt=athlete.localized_full_name,
                og_type="profile",
                structured_data=structured,
            )
        )
        return ctx


class PublicMedalWinnersView(ListView):
    model = Medal
    template_name = "public/medal_winners.html"
    context_object_name = "medals"
    paginate_by = getattr(settings, "PUBLIC_PAGE_SIZE", 12)

    def get_queryset(self):
        qs = Medal.objects.publicly_visible().select_related("member", "competition")
        q = (self.request.GET.get("q") or "").strip()
        medal_type = (self.request.GET.get("medal_type") or "").strip()
        discipline = (self.request.GET.get("discipline") or "").strip()
        competition_id = (self.request.GET.get("competition") or "").strip()
        sort = (self.request.GET.get("sort") or "-award_date").strip()

        if q:
            qs = qs.filter(
                Q(member__first_name__icontains=q)
                | Q(member__last_name__icontains=q)
                | Q(member__first_name_ja__icontains=q)
                | Q(member__last_name_ja__icontains=q)
                | Q(competition_name__icontains=q)
                | Q(competition_name_ja__icontains=q)
            )
        if medal_type in dict(MedalType.choices):
            qs = qs.filter(medal_type=medal_type)
        if discipline in dict(Discipline.choices):
            qs = qs.filter(discipline=discipline)
        if competition_id.isdigit():
            qs = qs.filter(competition_id=int(competition_id))

        if sort == "award_date":
            return qs.order_by("award_date", "id")
        return qs.order_by("-award_date", "-id")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = Medal.objects.publicly_visible()
        ctx.update(
            {
                "totals": {
                    "gold": base.filter(medal_type=MedalType.GOLD).count(),
                    "silver": base.filter(medal_type=MedalType.SILVER).count(),
                    "bronze": base.filter(medal_type=MedalType.BRONZE).count(),
                    "other": base.filter(medal_type=MedalType.OTHER).count(),
                },
                "medal_types": MedalType.choices,
                "disciplines": Discipline.choices,
                "competitions": Competition.objects.filter(is_published=True).order_by(
                    "-start_date"
                ),
                "filters": {
                    "q": (self.request.GET.get("q") or "").strip(),
                    "medal_type": (self.request.GET.get("medal_type") or "").strip(),
                    "discipline": (self.request.GET.get("discipline") or "").strip(),
                    "competition": (self.request.GET.get("competition") or "").strip(),
                    "sort": (self.request.GET.get("sort") or "-award_date").strip(),
                },
            }
        )
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.MEDAL_WINNERS,
                default_title=_("Medal Winners & Honor Roll"),
                default_description=_(
                    "Official verified Gold, Silver, and Bronze medal winners of TECHWANDO Club."
                ),
            )
        )
        return ctx


class PublicBeltAchievementsView(ListView):
    model = BeltHistory
    template_name = "public/belt_achievements.html"
    context_object_name = "belt_records"
    paginate_by = getattr(settings, "PUBLIC_PAGE_SIZE", 12)

    def get_queryset(self):
        qs = BeltHistory.objects.publicly_visible().select_related("member", "belt_type")
        discipline = (self.request.GET.get("discipline") or "").strip()
        belt_id = (self.request.GET.get("belt") or "").strip()
        dan_only = self.request.GET.get("dan_only") == "1"
        q = (self.request.GET.get("q") or "").strip()

        if discipline in dict(Discipline.choices):
            qs = qs.filter(discipline=discipline)
        if belt_id.isdigit():
            qs = qs.filter(belt_type_id=int(belt_id))
        if dan_only:
            qs = qs.filter(belt_type__is_black_belt=True)
        if q:
            qs = qs.filter(
                Q(member__first_name__icontains=q)
                | Q(member__last_name__icontains=q)
                | Q(member__first_name_ja__icontains=q)
                | Q(member__last_name_ja__icontains=q)
            )
        return qs.order_by("-award_date", "-belt_type__rank_order")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "disciplines": Discipline.choices,
                "belt_types": BeltType.objects.filter(is_active=True).order_by(
                    "discipline", "-rank_order"
                ),
                "filters": {
                    "q": (self.request.GET.get("q") or "").strip(),
                    "discipline": (self.request.GET.get("discipline") or "").strip(),
                    "belt": (self.request.GET.get("belt") or "").strip(),
                    "dan_only": self.request.GET.get("dan_only") == "1",
                },
            }
        )
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.BELT_ACHIEVEMENTS,
                default_title=_("Official Belt Promotions & Black Belt Registry"),
                default_description=_(
                    "Approved belt rank promotions and Dan black belt recipients at TECHWANDO."
                ),
            )
        )
        return ctx


class PublicCompetitionResultsView(ListView):
    model = Competition
    template_name = "public/competition_results.html"
    context_object_name = "competitions"
    paginate_by = 8

    def get_queryset(self):
        qs = Competition.objects.filter(is_published=True).order_by("-start_date")
        discipline = (self.request.GET.get("discipline") or "").strip()
        if discipline in dict(Discipline.choices):
            qs = qs.filter(discipline=discipline)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        comp_list = list(ctx["competitions"])
        comp_ids = [c.id for c in comp_list]

        participations = (
            CompetitionParticipation.objects.publicly_visible()
            .filter(competition_id__in=comp_ids)
            .select_related("member")
            .order_by("placement", "id")
        )
        medals = (
            Medal.objects.publicly_visible()
            .filter(competition_id__in=comp_ids)
            .select_related("member")
            .order_by("medal_type", "-award_date")
        )

        part_map: dict[int, list] = {cid: [] for cid in comp_ids}
        for p in participations:
            part_map[p.competition_id].append(p)
        medal_map: dict[int, list] = {cid: [] for cid in comp_ids}
        for m in medals:
            medal_map[m.competition_id].append(m)

        for c in comp_list:
            c.public_participations = part_map.get(c.id, [])
            c.public_medals = medal_map.get(c.id, [])

        ctx["disciplines"] = Discipline.choices
        ctx["selected_discipline"] = (self.request.GET.get("discipline") or "").strip()
        ctx.update(
            build_seo_context(
                self.request,
                route_key=RouteKey.COMPETITION_RESULTS,
                default_title=_("Championship & Competition Results"),
                default_description=_(
                    "Verified TECHWANDO team results, tournament standings, and medalists."
                ),
            )
        )
        return ctx

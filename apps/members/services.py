"""Services for membership number generation, profile management, and approval."""
from __future__ import annotations

import secrets

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.audit_logs.services import log_audit_event
from apps.core.models import ReviewLog
from apps.core.permissions import can_manage_members
from apps.members.models import MemberProfile, MembershipStatus
from apps.notifications.models import NotificationType
from apps.notifications.services import NotificationService


def generate_membership_number() -> str:
    """Generate a unique, sequential-style human-readable membership number."""
    year = timezone.localdate().year
    prefix = f"TW-{year}-"
    latest = (
        MemberProfile.objects.filter(membership_number__startswith=prefix)
        .order_by("-membership_number")
        .values_list("membership_number", flat=True)
        .first()
    )
    seq = 1
    if latest:
        tail = latest.replace(prefix, "")
        if tail.isdigit():
            seq = int(tail) + 1
    candidate = f"{prefix}{seq:05d}"
    if MemberProfile.objects.filter(membership_number=candidate).exists():
        candidate = f"{prefix}{seq:05d}-{secrets.token_hex(2).upper()}"
    return candidate


@transaction.atomic
def create_member_profile_with_application(
    *,
    user,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    primary_discipline: str = "TAEKWONDO",
    initial_status: str = MembershipStatus.PENDING,
    actor=None,
    request=None,
) -> MemberProfile:
    """Create a MemberProfile with a unique membership number and initial ReviewLog."""
    fn = (first_name or user.first_name or user.get_short_name()).strip()
    ln = (last_name or user.last_name or "").strip()

    profile = None
    for _ in range(5):
        mem_no = generate_membership_number()
        slug = mem_no.lower()
        try:
            with transaction.atomic():
                profile = MemberProfile.objects.create(
                    user=user,
                    first_name=fn,
                    last_name=ln or "-",
                    slug=slug,
                    phone=phone,
                    primary_discipline=primary_discipline,
                    membership_number=mem_no,
                    membership_status=initial_status,
                    reviewer=actor if initial_status == MembershipStatus.APPROVED else None,
                    reviewed_at=timezone.now()
                    if initial_status == MembershipStatus.APPROVED
                    else None,
                )
            break
        except IntegrityError:
            continue

    if profile is None:
        mem_no = f"TW-{timezone.localdate().year}-{secrets.token_hex(4).upper()}"
        profile = MemberProfile.objects.create(
            user=user,
            first_name=fn,
            last_name=ln or "-",
            slug=mem_no.lower(),
            phone=phone,
            primary_discipline=primary_discipline,
            membership_number=mem_no,
            membership_status=initial_status,
        )

    ct = ContentType.objects.get_for_model(MemberProfile)
    ReviewLog.objects.create(
        content_type=ct,
        object_id=profile.pk,
        target_repr=str(profile)[:255],
        event_type=ReviewLog.EventType.SUBMITTED,
        previous_status="",
        new_status=initial_status,
        reviewer=actor or user,
        note="",
    )
    return profile


def ensure_member_profile(user) -> MemberProfile:
    """Fetch or lazily create a MemberProfile for an existing authenticated user."""
    try:
        return user.member_profile
    except MemberProfile.DoesNotExist:
        initial = (
            MembershipStatus.APPROVED if user.is_admin_role else MembershipStatus.PENDING
        )
        return create_member_profile_with_application(
            user=user,
            first_name=user.first_name,
            last_name=user.last_name,
            initial_status=initial,
            actor=user,
        )


@transaction.atomic
def review_membership_application(
    *,
    profile: MemberProfile,
    reviewer,
    new_status: str,
    note: str = "",
    request=None,
) -> ReviewLog:
    """Approve, reject, request revision on, or suspend a membership application."""
    if not can_manage_members(reviewer):
        raise PermissionDenied(_("You are not authorized to review membership applications."))

    if new_status not in dict(MembershipStatus.choices):
        raise ValidationError(_("Invalid membership status."))

    locked = MemberProfile.objects.select_for_update().select_related("user").get(pk=profile.pk)
    if locked.user_id == reviewer.id and new_status == MembershipStatus.APPROVED:
        raise PermissionDenied(_("You cannot approve your own membership application."))

    prev_status = locked.membership_status
    cleaned_note = (note or "").strip()

    locked.membership_status = new_status
    locked.admin_note = cleaned_note
    locked.reviewer = reviewer
    locked.reviewed_at = timezone.now()
    locked.save(
        update_fields=[
            "membership_status",
            "admin_note",
            "reviewer",
            "reviewed_at",
            "updated_at",
        ]
    )

    profile.membership_status = locked.membership_status
    profile.admin_note = locked.admin_note
    profile.reviewer = locked.reviewer
    profile.reviewed_at = locked.reviewed_at

    ct = ContentType.objects.get_for_model(MemberProfile)
    review_log = ReviewLog.objects.create(
        content_type=ct,
        object_id=locked.pk,
        target_repr=str(locked)[:255],
        event_type=ReviewLog.EventType.REVIEWED,
        previous_status=prev_status,
        new_status=new_status,
        reviewer=reviewer,
        note=cleaned_note,
    )

    log_audit_event(
        actor=reviewer,
        action=f"MEMBERSHIP_{new_status}",
        instance=locked,
        previous_state={"membership_status": prev_status},
        new_state={"membership_status": new_status, "admin_note": cleaned_note},
        request=request,
    )

    status_fa = {
        MembershipStatus.APPROVED: "تأیید شد",
        MembershipStatus.REJECTED: "رد شد",
        MembershipStatus.NEEDS_REVISION: "نیازمند تکمیل اطلاعات است",
        MembershipStatus.SUSPENDED: "به حالت تعلیق درآمد",
        MembershipStatus.PENDING: "در انتظار بررسی قرار گرفت",
    }.get(new_status, new_status)

    status_ko = {
        MembershipStatus.APPROVED: "승인되었습니다",
        MembershipStatus.REJECTED: "거절되었습니다",
        MembershipStatus.NEEDS_REVISION: "정보 수정이 필요합니다",
        MembershipStatus.SUSPENDED: "일시 중지되었습니다",
        MembershipStatus.PENDING: "검토 대기 중입니다",
    }.get(new_status, new_status)

    fa_msg = f"وضعیت عضویت شما ({locked.membership_number}) {status_fa}."
    ko_msg = f"회원 자격 ({locked.membership_number}): {status_ko}."
    if cleaned_note:
        fa_msg += f" یادداشت مدیریت: {cleaned_note}"
        ko_msg += f" 관리자 의견: {cleaned_note}"

    NotificationService.notify_user(
        recipient=locked.user,
        message_fa=fa_msg,
        message_ko=ko_msg,
        notification_type=NotificationType.MEMBERSHIP_UPDATE,
        target_url=reverse("members:dashboard"),
    )
    return review_log

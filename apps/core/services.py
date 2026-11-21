"""Transactional moderation, review logging, notification, and audit workflow."""
from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import ApprovalStatus, ReviewLog
from apps.core.permissions import can_moderate_submission

STATUS_LABELS_FA = {
    ApprovalStatus.PENDING: "در انتظار بررسی",
    ApprovalStatus.APPROVED: "تأیید شده",
    ApprovalStatus.REJECTED: "رد شده",
    ApprovalStatus.NEEDS_REVISION: "نیازمند اصلاح",
}

STATUS_LABELS_KO = {
    ApprovalStatus.PENDING: "검토 대기",
    ApprovalStatus.APPROVED: "승인됨",
    ApprovalStatus.REJECTED: "거절됨",
    ApprovalStatus.NEEDS_REVISION: "수정 요청",
}

MODEL_LABELS_FA = {
    "medal": "مدال",
    "achievement": "دستاورد ورزشی",
    "belthistory": "ارتقای کمربند",
    "socialactivity": "فعالیت اجتماعی",
    "competitionparticipation": "حضور در مسابقه",
    "memberprofile": "درخواست عضویت",
}

MODEL_LABELS_KO = {
    "medal": "메달",
    "achievement": "스포츠 성과",
    "belthistory": "승급 신청",
    "socialactivity": "사회 활동",
    "competitionparticipation": "대회 참가 기록",
    "memberprofile": "회원 가입 신청",
}


class ModerationService:
    """Centralized, transactional moderation engine for all member submissions."""

    @staticmethod
    @transaction.atomic
    def record_member_submission(
        submission,
        actor,
        *,
        is_resubmission: bool = False,
        request=None,
    ) -> ReviewLog:
        """
        Enforce PENDING status on member create/edit, write ReviewLog + AuditLog,
        and notify authorized moderators/managers.
        """
        from apps.audit_logs.services import log_audit_event
        from apps.notifications.services import NotificationService

        prev_status = submission.approval_status if is_resubmission else ""
        submission.approval_status = ApprovalStatus.PENDING
        submission.reviewer = None
        submission.reviewed_at = None
        submission.save(
            update_fields=["approval_status", "reviewer", "reviewed_at", "updated_at"]
        )

        ct = ContentType.objects.get_for_model(submission.__class__)
        model_key = submission._meta.model_name
        event = (
            ReviewLog.EventType.RESUBMITTED
            if is_resubmission
            else ReviewLog.EventType.SUBMITTED
        )
        review_log = ReviewLog.objects.create(
            content_type=ct,
            object_id=submission.pk,
            target_repr=str(submission)[:255],
            event_type=event,
            previous_status=prev_status,
            new_status=ApprovalStatus.PENDING,
            reviewer=actor,
            note="",
        )

        log_audit_event(
            actor=actor,
            action="SUBMISSION_RESUBMITTED" if is_resubmission else "SUBMISSION_CREATED",
            instance=submission,
            previous_state={"approval_status": prev_status} if prev_status else {},
            new_state={"approval_status": ApprovalStatus.PENDING},
            request=request,
        )

        fa_kind = MODEL_LABELS_FA.get(model_key, model_key)
        ko_kind = MODEL_LABELS_KO.get(model_key, model_key)
        member_name = submission.member.full_name
        NotificationService.notify_moderators(
            model_key=model_key,
            message_fa=f"ثبت جدید {fa_kind} توسط {member_name}: «{submission}» در انتظار بررسی است.",
            message_ko=f"{member_name} 님이 새 {ko_kind} 「{submission}」을 제출했습니다. 검토 대기 중입니다.",
            notification_type="SUBMISSION_PENDING",
            target_url=reverse(
                "accounts:admin_review_submission",
                kwargs={"model_type": model_key, "pk": submission.pk},
            ),
            exclude_user_id=actor.id if actor else None,
        )
        return review_log

    @staticmethod
    @transaction.atomic
    def request_correction(submission, actor, reason: str, *, request=None) -> ReviewLog:
        """
        Allow the owning member to request a correction on an APPROVED or REJECTED
        record. Transitions the record to NEEDS_REVISION/PENDING review safely without
        granting self-approval.
        """
        from apps.audit_logs.services import log_audit_event
        from apps.notifications.services import NotificationService

        if submission.member.user_id != actor.id:
            raise PermissionDenied(_("You may only request corrections for your own records."))

        cleaned_reason = (reason or "").strip()
        if not cleaned_reason:
            raise ValidationError(_("Please describe the correction needed."))

        locked = submission.__class__.objects.select_for_update().get(pk=submission.pk)
        previous_status = locked.approval_status
        locked.correction_request = cleaned_reason
        locked.approval_status = ApprovalStatus.NEEDS_REVISION
        locked.save(
            update_fields=["correction_request", "approval_status", "updated_at"]
        )

        # Keep caller reference in sync
        submission.correction_request = locked.correction_request
        submission.approval_status = locked.approval_status

        ct = ContentType.objects.get_for_model(locked.__class__)
        model_key = locked._meta.model_name
        review_log = ReviewLog.objects.create(
            content_type=ct,
            object_id=locked.pk,
            target_repr=str(locked)[:255],
            event_type=ReviewLog.EventType.CORRECTION_REQUESTED,
            previous_status=previous_status,
            new_status=ApprovalStatus.NEEDS_REVISION,
            reviewer=actor,
            note=cleaned_reason,
        )

        log_audit_event(
            actor=actor,
            action="CORRECTION_REQUESTED",
            instance=locked,
            previous_state={"approval_status": previous_status},
            new_state={
                "approval_status": ApprovalStatus.NEEDS_REVISION,
                "correction_request": cleaned_reason,
            },
            request=request,
        )

        fa_kind = MODEL_LABELS_FA.get(model_key, model_key)
        ko_kind = MODEL_LABELS_KO.get(model_key, model_key)
        NotificationService.notify_moderators(
            model_key=model_key,
            message_fa=f"درخواست اصلاح برای {fa_kind} «{locked}» توسط {locked.member.full_name} ثبت شد.",
            message_ko=f"{locked.member.full_name} 님이 {ko_kind} 「{locked}」에 대한 수정을 요청했습니다.",
            notification_type="CORRECTION_REQUEST",
            target_url=reverse(
                "accounts:admin_review_submission",
                kwargs={"model_type": model_key, "pk": locked.pk},
            ),
            exclude_user_id=actor.id,
        )
        return review_log

    @staticmethod
    @transaction.atomic
    def review_submission(
        submission,
        reviewer,
        new_status: str,
        note: str = "",
        *,
        request=None,
    ) -> ReviewLog:
        """
        Approve, reject, or request revision on a member submission.
        Server-side guarantees:
        - Reviewer must hold an authorized administrative/moderator role & permission.
        - A user can NEVER review or approve their own submission.
        - Updates status, reviewer, reviewed_at, admin_note atomically.
        - Records immutable ReviewLog and AuditLog entries.
        - Dispatches localized notification to the member.
        """
        from apps.audit_logs.services import log_audit_event
        from apps.notifications.services import NotificationService

        model_key = submission._meta.model_name
        if not can_moderate_submission(reviewer, model_key):
            raise PermissionDenied(_("You are not authorized to review this submission."))

        valid_statuses = {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.NEEDS_REVISION,
            ApprovalStatus.PENDING,
        }
        if new_status not in valid_statuses:
            raise ValidationError(_("Invalid approval status."))

        locked = (
            submission.__class__.objects.select_for_update()
            .select_related("member", "member__user")
            .get(pk=submission.pk)
        )

        if locked.member.user_id == reviewer.id:
            raise PermissionDenied(_("You cannot review or approve your own submission."))

        cleaned_note = (note or "").strip()
        prev_status = locked.approval_status
        prev_note = locked.admin_note
        now = timezone.now()

        locked.approval_status = new_status
        locked.admin_note = cleaned_note
        locked.reviewer = reviewer
        locked.reviewed_at = now
        if new_status == ApprovalStatus.APPROVED:
            locked.correction_request = ""
        locked.save(
            update_fields=[
                "approval_status",
                "admin_note",
                "reviewer",
                "reviewed_at",
                "correction_request",
                "updated_at",
            ]
        )

        # Synchronize in-memory instance
        submission.approval_status = locked.approval_status
        submission.admin_note = locked.admin_note
        submission.reviewer = locked.reviewer
        submission.reviewed_at = locked.reviewed_at
        submission.correction_request = locked.correction_request

        ct = ContentType.objects.get_for_model(locked.__class__)
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

        action_map = {
            ApprovalStatus.APPROVED: "SUBMISSION_APPROVED",
            ApprovalStatus.REJECTED: "SUBMISSION_REJECTED",
            ApprovalStatus.NEEDS_REVISION: "SUBMISSION_REVISION_REQUESTED",
            ApprovalStatus.PENDING: "SUBMISSION_RESET_PENDING",
        }
        log_audit_event(
            actor=reviewer,
            action=action_map[new_status],
            instance=locked,
            previous_state={"approval_status": prev_status, "admin_note": prev_note},
            new_state={"approval_status": new_status, "admin_note": cleaned_note},
            request=request,
        )

        fa_kind = MODEL_LABELS_FA.get(model_key, model_key)
        ko_kind = MODEL_LABELS_KO.get(model_key, model_key)
        fa_status = STATUS_LABELS_FA.get(new_status, new_status)
        ko_status = STATUS_LABELS_KO.get(new_status, new_status)

        fa_msg = f"وضعیت {fa_kind} «{locked}» به «{fa_status}» تغییر یافت."
        ko_msg = f"{ko_kind} 「{locked}」의 심사 결과가 「{ko_status}」로 변경되었습니다."
        if cleaned_note:
            fa_msg += f" یادداشت مدیر: {cleaned_note}"
            ko_msg += f" 관리자 의견: {cleaned_note}"

        notif_type_map = {
            ApprovalStatus.APPROVED: "SUBMISSION_APPROVED",
            ApprovalStatus.REJECTED: "SUBMISSION_REJECTED",
            ApprovalStatus.NEEDS_REVISION: "SUBMISSION_REVISION",
            ApprovalStatus.PENDING: "SUBMISSION_PENDING",
        }
        member_url = getattr(locked, "get_member_url", lambda: reverse("members:dashboard"))()

        NotificationService.notify_user(
            recipient=locked.member.user,
            message_fa=fa_msg,
            message_ko=ko_msg,
            notification_type=notif_type_map[new_status],
            target_url=member_url,
        )
        return review_log

    @staticmethod
    def get_logs_for_object(obj):
        ct = ContentType.objects.get_for_model(obj.__class__)
        return ReviewLog.objects.filter(content_type=ct, object_id=obj.pk).select_related(
            "reviewer"
        )

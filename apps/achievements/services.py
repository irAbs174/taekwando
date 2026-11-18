"""Business services for member achievement submissions."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.achievements.models import Achievement
from apps.core.services import ModerationService


class AchievementService:
    @staticmethod
    @transaction.atomic
    def submit_achievement(*, member, form, actor, request=None) -> Achievement:
        record: Achievement = form.save(commit=False)
        record.member = member
        record.save()
        ModerationService.record_member_submission(
            record, actor=actor, is_resubmission=False, request=request
        )
        return record

    @staticmethod
    @transaction.atomic
    def update_achievement(
        *, record: Achievement, member, form, actor, request=None
    ) -> Achievement:
        if record.member_id != member.id or not record.can_member_edit:
            raise PermissionDenied
        updated: Achievement = form.save(commit=False)
        updated.member = member
        updated.save()
        ModerationService.record_member_submission(
            updated, actor=actor, is_resubmission=True, request=request
        )
        return updated

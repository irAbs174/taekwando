"""Business services for member social activity submissions."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.activities.models import SocialActivity
from apps.core.services import ModerationService


class ActivityService:
    @staticmethod
    @transaction.atomic
    def submit_activity(*, member, form, actor, request=None) -> SocialActivity:
        record: SocialActivity = form.save(commit=False)
        record.member = member
        record.save()
        ModerationService.record_member_submission(
            record, actor=actor, is_resubmission=False, request=request
        )
        return record

    @staticmethod
    @transaction.atomic
    def update_activity(
        *, record: SocialActivity, member, form, actor, request=None
    ) -> SocialActivity:
        if record.member_id != member.id or not record.can_member_edit:
            raise PermissionDenied
        updated: SocialActivity = form.save(commit=False)
        updated.member = member
        updated.save()
        ModerationService.record_member_submission(
            updated, actor=actor, is_resubmission=True, request=request
        )
        return updated

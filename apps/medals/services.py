"""Business services for submitting and updating athlete medals."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.core.services import ModerationService
from apps.medals.models import Medal


class MedalService:
    @staticmethod
    @transaction.atomic
    def submit_medal(*, member, form, actor, request=None) -> Medal:
        medal: Medal = form.save(commit=False)
        medal.member = member
        medal.save()
        ModerationService.record_member_submission(
            medal, actor=actor, is_resubmission=False, request=request
        )
        return medal

    @staticmethod
    @transaction.atomic
    def update_medal(*, record: Medal, member, form, actor, request=None) -> Medal:
        if record.member_id != member.id or not record.can_member_edit:
            raise PermissionDenied
        updated: Medal = form.save(commit=False)
        updated.member = member
        updated.save()
        ModerationService.record_member_submission(
            updated, actor=actor, is_resubmission=True, request=request
        )
        return updated

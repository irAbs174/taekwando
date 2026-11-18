"""Business services for competition participation submissions."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.competitions.models import CompetitionParticipation
from apps.core.services import ModerationService


class CompetitionService:
    @staticmethod
    @transaction.atomic
    def submit_participation(*, member, form, actor, request=None) -> CompetitionParticipation:
        record: CompetitionParticipation = form.save(commit=False)
        record.member = member
        record.save()
        ModerationService.record_member_submission(
            record, actor=actor, is_resubmission=False, request=request
        )
        return record

    @staticmethod
    @transaction.atomic
    def update_participation(
        *, record: CompetitionParticipation, member, form, actor, request=None
    ) -> CompetitionParticipation:
        if record.member_id != member.id or not record.can_member_edit:
            raise PermissionDenied
        updated: CompetitionParticipation = form.save(commit=False)
        updated.member = member
        updated.save()
        ModerationService.record_member_submission(
            updated, actor=actor, is_resubmission=True, request=request
        )
        return updated

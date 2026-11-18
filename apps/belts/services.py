"""Business services for submitting and updating belt promotion records."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.belts.models import BeltHistory
from apps.core.services import ModerationService


class BeltService:
    @staticmethod
    @transaction.atomic
    def submit_belt_promotion(*, member, form, actor, request=None) -> BeltHistory:
        record: BeltHistory = form.save(commit=False)
        record.member = member
        record.discipline = record.belt_type.discipline
        record.save()
        ModerationService.record_member_submission(
            record, actor=actor, is_resubmission=False, request=request
        )
        return record

    @staticmethod
    @transaction.atomic
    def update_belt_promotion(*, record: BeltHistory, member, form, actor, request=None) -> BeltHistory:
        if record.member_id != member.id or not record.can_member_edit:
            raise PermissionDenied
        updated: BeltHistory = form.save(commit=False)
        updated.member = member
        updated.discipline = updated.belt_type.discipline
        updated.save()
        ModerationService.record_member_submission(
            updated, actor=actor, is_resubmission=True, request=request
        )
        return updated

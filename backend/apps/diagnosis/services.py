from typing import Any
from django.db import transaction
from rest_framework import serializers

from apps.kb.models import Cause
from apps.kb.loader import load_kb
from apps.diagnosis.models import Diagnosis
from apps.core.errors import ApiException
from backend.engine.types import ConvState, DiagnosisData
from backend.engine.scoring import rank, next_question, is_conclusive, build_diagnosis


class DiagnosisSerializer(serializers.ModelSerializer):
    top_cause_key = serializers.CharField(source='top_cause.key', read_only=True)
    top_cause_label = serializers.CharField(source='top_cause.label', read_only=True)
    service = serializers.SerializerMethodField()

    class Meta:
        model = Diagnosis
        fields = [
            'id',
            'conversation_id',
            'top_cause_key',
            'top_cause_label',
            'confidence',
            'severity',
            'ranked',
            'evidence_hash',
            'safety_alert',
            'service',
            'created_at',
        ]

    def get_service(self, obj: Diagnosis) -> dict[str, Any]:
        svc = obj.top_cause.service
        return {
            'key': svc.key,
            'name': svc.name,
            'description': svc.description,
            'price_min': svc.price_min,
            'price_max': svc.price_max,
            'duration_hours': svc.duration_hours,
            'currency': 'INR',
        }


def save_diagnosis(conversation: Any, diag_data: DiagnosisData) -> Diagnosis:
    # Dedupe by evidence_hash for this conversation
    existing = Diagnosis.objects.filter(
        conversation=conversation,
        evidence_hash=diag_data.evidence_hash,
    ).first()
    if existing:
        return existing

    top_key = diag_data.top.get("cause_key")
    cause_obj = Cause.objects.select_related('service').get(key=top_key)

    return Diagnosis.objects.create(
        conversation=conversation,
        top_cause=cause_obj,
        confidence=diag_data.top.get("confidence", 0.0),
        severity=diag_data.severity,
        ranked=diag_data.ranked,
        evidence_hash=diag_data.evidence_hash,
        safety_alert=diag_data.safety_alert or "",
    )


def diagnose(conversation: Any, force: bool = False) -> Diagnosis:
    kb = load_kb()
    state = ConvState.from_dict(conversation.slots)

    if not state.symptoms:
        raise ApiException(
            code="no_symptoms",
            message="Cannot generate diagnosis without identified symptoms.",
            status_code=400,
        )

    ranked = rank(kb, state)
    if not ranked:
        raise ApiException(
            code="no_matching_causes",
            message="No matching causes found for the given symptoms.",
            status_code=400,
        )

    next_q = next_question(kb, state, ranked)
    conclusive = is_conclusive(state, ranked, next_q)

    if not conclusive and not force:
        next_q_dict: dict[str, Any] | None = None
        if next_q:
            next_q_dict = {
                "key": next_q.key,
                "text": next_q.text,
                "options": [
                    {
                        "id": opt.id,
                        "label": opt.label,
                        "keywords": list(opt.keywords),
                    }
                    for opt in next_q.options
                ],
            }

        top_ranked_list = [
            {
                "cause_key": r.cause_key,
                "confidence": r.confidence,
                "why": r.why,
            }
            for r in ranked[:3]
        ]

        raise ApiException(
            code="needs_more_info",
            message="More information is required to reach a conclusive diagnosis.",
            status_code=409,
            details={
                "next_question": next_q_dict,
                "ranked": top_ranked_list,
            },
        )

    diag_data = build_diagnosis(kb, state, ranked)
    with transaction.atomic():
        diag_obj = save_diagnosis(conversation, diag_data)
        state.last_diagnosis_id = str(diag_obj.id)
        conversation.slots = state.to_dict()
        conversation.save(update_fields=['slots'])

    return diag_obj

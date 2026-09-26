from typing import Any
from rest_framework import serializers
from apps.diagnosis.models import Diagnosis


SEVERITY_LABELS = {1: "low", 2: "medium", 3: "high", 4: "critical"}


class DiagnosisRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=True)
    force = serializers.BooleanField(required=False, default=False)


class DiagnosisSerializer(serializers.ModelSerializer):
    top_cause_key = serializers.CharField(source='top_cause.key', read_only=True)
    top_cause_label = serializers.CharField(source='top_cause.label', read_only=True)
    service = serializers.SerializerMethodField()
    top = serializers.SerializerMethodField()
    ranked = serializers.SerializerMethodField()
    severity_label = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    final = serializers.SerializerMethodField()

    class Meta:
        model = Diagnosis
        fields = [
            'id',
            'conversation_id',
            'top_cause_key',
            'top_cause_label',
            'confidence',
            'severity',
            'severity_label',
            'ranked',
            'evidence_hash',
            'safety_alert',
            'service',
            'top',
            'source',
            'final',
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

    def get_top(self, obj: Diagnosis) -> dict[str, Any]:
        return {
            'cause_key': obj.top_cause.key,
            'label': obj.top_cause.label,
            'description': obj.top_cause.description,
            'confidence': obj.confidence,
        }

    def get_ranked(self, obj: Diagnosis) -> list[dict[str, Any]]:
        stored = obj.ranked or []
        if stored:
            return stored
        return [{
            'cause_key': obj.top_cause.key,
            'label': obj.top_cause.label,
            'confidence': obj.confidence,
            'why': [],
        }]

    def get_severity_label(self, obj: Diagnosis) -> str:
        return SEVERITY_LABELS.get(int(obj.severity or 2), "medium")

    def get_source(self, obj: Diagnosis) -> str:
        slots = obj.conversation.slots if obj.conversation_id else {}
        media = int((slots or {}).get('media_analyses', 0) or 0)
        extracts = int((slots or {}).get('ai_extract_calls', 0) or 0)
        return "rules+ai" if (media or extracts) else "rules"

    def get_final(self, obj: Diagnosis) -> bool:
        return True

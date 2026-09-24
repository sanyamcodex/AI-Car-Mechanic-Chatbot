from rest_framework import serializers
from apps.diagnosis.services import DiagnosisSerializer


class DiagnosisRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=True)
    force = serializers.BooleanField(required=False, default=False)

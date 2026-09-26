from typing import Any
from rest_framework import serializers
from apps.chat.models import Conversation, Message
from apps.diagnosis.serializers import DiagnosisSerializer
from apps.booking.serializers import BookingSerializer


class MessageSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source='sender', read_only=True)

    class Meta:
        model = Message
        fields = [
            'id',
            'sender',
            'role',
            'text',
            'kind',
            'meta',
            'client_msg_id',
            'created_at',
        ]


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'status',
            'state',
            'message_count',
            'last_message',
            'created_at',
            'updated_at',
        ]

    def get_message_count(self, obj: Conversation) -> int:
        cached = getattr(obj, '_prefetched_objects_cache', {}).get('messages')
        if cached is not None:
            return len(cached)
        return obj.messages.count()

    def get_last_message(self, obj: Conversation) -> str:
        cached = getattr(obj, '_prefetched_objects_cache', {}).get('messages')
        if cached is not None:
            return cached[-1].text if cached else ""
        last = obj.messages.order_by('-created_at').first()
        return last.text if last else ""

    def get_state(self, obj: Conversation) -> str:
        slots = obj.slots or {}
        return slots.get('state') or 'INTAKE'


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    suggested_replies = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    vehicle = serializers.SerializerMethodField()
    diagnosis = serializers.SerializerMethodField()
    booking = serializers.SerializerMethodField()
    cta = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'status',
            'state',
            'vehicle',
            'slots',
            'messages',
            'suggested_replies',
            'diagnosis',
            'booking',
            'cta',
            'created_at',
            'updated_at',
        ]

    def get_state(self, obj: Conversation) -> str:
        return (obj.slots or {}).get('state') or 'INTAKE'

    def get_vehicle(self, obj: Conversation) -> dict[str, Any]:
        return (obj.slots or {}).get('vehicle') or {}

    def get_suggested_replies(self, obj: Conversation) -> list[dict[str, Any]]:
        last_bot = obj.messages.filter(sender='bot').order_by('-created_at').first()
        if last_bot and isinstance(last_bot.meta, dict):
            return last_bot.meta.get('suggested_replies', [])
        return []

    def get_diagnosis(self, obj: Conversation) -> dict[str, Any] | None:
        diag_id = (obj.slots or {}).get('last_diagnosis_id')
        diag = None
        if diag_id:
            from apps.diagnosis.models import Diagnosis
            diag = Diagnosis.objects.select_related('top_cause__service', 'conversation').filter(id=diag_id).first()
        if not diag:
            diag = obj.diagnoses.select_related('top_cause__service', 'conversation').order_by('-created_at').first()
        if not diag:
            return None
        return DiagnosisSerializer(diag).data

    def get_booking(self, obj: Conversation) -> dict[str, Any] | None:
        booking = obj.bookings.select_related('service', 'mechanic').order_by('-created_at').first()
        if not booking:
            return None
        return BookingSerializer(booking).data

    def get_cta(self, obj: Conversation) -> dict[str, Any] | None:
        state = (obj.slots or {}).get('state')
        diag_id = (obj.slots or {}).get('last_diagnosis_id')
        if state == 'BOOKING_OFFERED' and diag_id:
            return {'type': 'book_mechanic', 'diagnosis_id': str(diag_id)}
        return None


class ChatRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    client_msg_id = serializers.CharField(required=False, allow_blank=True, max_length=64, default="")
    message = serializers.CharField(required=False, allow_blank=True, default="")
    text = serializers.CharField(required=False, allow_blank=True, default="")
    choice = serializers.DictField(required=False, allow_null=True, default=None)
    upload_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )

    def validate(self, attrs: dict) -> dict:
        msg = (attrs.get("message") or attrs.get("text") or "").strip()
        attrs["text"] = msg
        if not msg and not attrs.get("choice") and not attrs.get("upload_ids"):
            raise serializers.ValidationError(
                "At least one of message, choice, or upload_ids is required."
            )
        return attrs


class ChatResponseSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    state = serializers.CharField(required=False)
    messages = MessageSerializer(many=True)
    suggested_replies = serializers.ListField(child=serializers.DictField(), default=list)
    diagnosis = DiagnosisSerializer(allow_null=True, required=False)
    cta = serializers.DictField(allow_null=True, required=False)
    meta = serializers.DictField(required=False)
    actions = serializers.DictField(allow_null=True, required=False)

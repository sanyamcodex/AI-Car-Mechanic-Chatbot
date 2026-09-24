from typing import Any
from rest_framework import serializers
from apps.chat.models import Conversation, Message
from apps.diagnosis.serializers import DiagnosisSerializer


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = [
            'id',
            'sender',
            'text',
            'kind',
            'meta',
            'client_msg_id',
            'created_at',
        ]


class ConversationSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'status',
            'message_count',
            'last_message',
            'created_at',
            'updated_at',
        ]

    def get_message_count(self, obj: Conversation) -> int:
        return obj.messages.count()

    def get_last_message(self, obj: Conversation) -> str:
        last = obj.messages.order_by('-created_at').first()
        return last.text if last else ""


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    suggested_replies = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'title',
            'status',
            'slots',
            'messages',
            'suggested_replies',
            'created_at',
            'updated_at',
        ]

    def get_suggested_replies(self, obj: Conversation) -> list[dict[str, Any]]:
        last_bot = obj.messages.filter(sender='bot').order_by('-created_at').first()
        if last_bot and isinstance(last_bot.meta, dict):
            return last_bot.meta.get('suggested_replies', [])
        return []


class ChatRequestSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    client_msg_id = serializers.CharField(required=False, allow_blank=True, max_length=64, default="")
    text = serializers.CharField(required=False, allow_blank=True, default="")
    choice = serializers.DictField(required=False, allow_null=True, default=None)
    upload_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )


class ChatResponseSerializer(serializers.Serializer):
    conversation_id = serializers.UUIDField()
    messages = MessageSerializer(many=True)
    suggested_replies = serializers.ListField(child=serializers.DictField(), default=list)
    diagnosis = DiagnosisSerializer(allow_null=True, required=False)
    actions = serializers.DictField(allow_null=True, required=False)

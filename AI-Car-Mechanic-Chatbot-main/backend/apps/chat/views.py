from uuid import UUID
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from apps.chat.models import Conversation
from apps.chat.serializers import (
    ChatRequestSerializer,
    ChatResponseSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
)
from apps.chat.services import handle_turn
from apps.core.errors import ApiException
from apps.core.throttles import ChatRateThrottle, AnonRateThrottle


class ChatView(APIView):
    throttle_classes = [ChatRateThrottle]

    @extend_schema(
        summary="Process Chat Turn",
        description="Receives user message or choice chip, runs deterministic engine, and returns replies/diagnosis.",
        request=ChatRequestSerializer,
        responses={
            200: ChatResponseSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        result = handle_turn(
            conversation_id=data.get('conversation_id'),
            client_msg_id=data.get('client_msg_id'),
            text=data.get('text'),
            choice=data.get('choice'),
            upload_ids=data.get('upload_ids'),
        )

        response_serializer = ChatResponseSerializer(result)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ConversationListView(APIView):
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="List Conversations",
        description="Lists active conversations. Can be filtered by a comma-separated list of IDs via ?ids=.",
        parameters=[
            OpenApiParameter(
                name='ids',
                type=str,
                location=OpenApiParameter.QUERY,
                description='Comma-separated UUID list to filter conversations',
                required=False,
            )
        ],
        responses={
            200: ConversationSerializer(many=True),
        },
    )
    def get(self, request, *args, **kwargs):
        qs = Conversation.objects.all()
        ids_param = request.query_params.get('ids', '').strip()
        if ids_param:
            valid_ids = []
            for item in ids_param.split(','):
                item = item.strip()
                try:
                    valid_ids.append(UUID(item))
                except ValueError:
                    pass
            qs = qs.filter(id__in=valid_ids)

        serializer = ConversationSerializer(qs[:20], many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConversationDetailView(APIView):
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Get Conversation Detail",
        description="Retrieves a conversation by UUID including all messages and last suggested replies.",
        responses={
            200: ConversationDetailSerializer,
            404: OpenApiResponse(description="Conversation not found"),
        },
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            conv = Conversation.objects.prefetch_related('messages').get(pk=pk)
        except Conversation.DoesNotExist:
            raise ApiException(
                code="not_found",
                message="Conversation not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConversationDetailSerializer(conv)
        return Response(serializer.data, status=status.HTTP_200_OK)

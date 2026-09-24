from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from apps.chat.models import Conversation
from apps.diagnosis.models import Diagnosis
from apps.diagnosis.serializers import DiagnosisRequestSerializer, DiagnosisSerializer
from apps.diagnosis.services import diagnose
from apps.core.errors import ApiException
from apps.core.throttles import ChatRateThrottle, AnonRateThrottle


class DiagnosisView(APIView):
    throttle_classes = [ChatRateThrottle]

    @extend_schema(
        summary="Request Diagnosis",
        description="Generates or forces a diagnosis for the active conversation.",
        request=DiagnosisRequestSerializer,
        responses={
            200: DiagnosisSerializer,
            400: OpenApiResponse(description="Bad request / No symptoms"),
            404: OpenApiResponse(description="Conversation not found"),
            409: OpenApiResponse(description="More info needed"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = DiagnosisRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv_id = serializer.validated_data["conversation_id"]
        force = serializer.validated_data.get("force", False)

        try:
            conversation = Conversation.objects.get(id=conv_id)
        except Conversation.DoesNotExist:
            raise ApiException(
                code="not_found",
                message="Conversation not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        diag = diagnose(conversation, force=force)
        return Response(DiagnosisSerializer(diag).data, status=status.HTTP_200_OK)


class DiagnosisDetailView(APIView):
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Get Diagnosis Details",
        description="Retrieves a specific diagnosis by its UUID.",
        responses={
            200: DiagnosisSerializer,
            404: OpenApiResponse(description="Diagnosis not found"),
        },
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            diag = Diagnosis.objects.select_related('top_cause__service').get(pk=pk)
        except Diagnosis.DoesNotExist:
            raise ApiException(
                code="not_found",
                message="Diagnosis not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(DiagnosisSerializer(diag).data, status=status.HTTP_200_OK)

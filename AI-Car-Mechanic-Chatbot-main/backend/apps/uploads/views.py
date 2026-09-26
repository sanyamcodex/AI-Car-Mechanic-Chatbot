from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.chat.models import Conversation
from apps.uploads.models import Upload
from apps.uploads.validators import validate_and_process_upload
from apps.uploads.serializers import UploadSerializer, UploadCreateSerializer
from apps.core.errors import ApiException
from apps.core.throttles import UploadRateThrottle, AnonRateThrottle


class UploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UploadRateThrottle]

    @extend_schema(
        summary="Upload Media File",
        description="Upload an image, audio, or video file for mechanical defect diagnosis.",
        request=UploadCreateSerializer,
        responses={
            201: UploadSerializer,
            400: OpenApiResponse(description="Invalid file"),
            413: OpenApiResponse(description="File too large"),
            415: OpenApiResponse(description="Unsupported media type"),
        },
    )
    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            raise ApiException(
                code="missing_file",
                message="No file was provided in the upload request.",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        content, mime_type, kind, size_bytes, sha256 = validate_and_process_upload(uploaded_file)

        conv_id = request.data.get('conversation_id')
        conversation = None
        if conv_id:
            conversation, _ = Conversation.objects.get_or_create(id=conv_id)

        upload = Upload(
            conversation=conversation,
            original_name=uploaded_file.name or 'upload',
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            kind=kind,
        )
        upload.file.save(uploaded_file.name or 'upload', ContentFile(content), save=True)

        return Response(
            UploadSerializer(upload, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class UploadDetailView(APIView):
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Get Upload Details",
        description="Retrieves metadata and analysis status for an uploaded media file.",
        responses={
            200: UploadSerializer,
            404: OpenApiResponse(description="Upload not found"),
        },
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            upload = Upload.objects.get(pk=pk)
        except Upload.DoesNotExist:
            raise ApiException(
                code="not_found",
                message="Upload not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(UploadSerializer(upload).data, status=status.HTTP_200_OK)

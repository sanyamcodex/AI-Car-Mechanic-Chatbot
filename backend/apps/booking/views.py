from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from apps.booking.models import Booking
from apps.booking.serializers import BookingSerializer, BookingCreateSerializer
from apps.booking.services import create_booking
from apps.core.errors import ApiException
from apps.core.throttles import BookingRateThrottle, AnonRateThrottle


class BookingView(APIView):
    throttle_classes = [BookingRateThrottle]

    @extend_schema(
        summary="Create Mechanic Booking",
        description="Creates an appointment with an assigned specialist mechanic. Supports Idempotency-Key header.",
        parameters=[
            OpenApiParameter(
                name='Idempotency-Key',
                type=str,
                location=OpenApiParameter.HEADER,
                description='Optional client idempotency key to prevent double bookings',
                required=False,
            )
        ],
        request=BookingCreateSerializer,
        responses={
            201: BookingSerializer,
            400: OpenApiResponse(description="Validation error"),
            409: OpenApiResponse(description="Slot unavailable / Conflict"),
        },
    )
    def post(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        idempotency_key = (
            request.headers.get('Idempotency-Key')
            or request.headers.get('idempotency-key')
            or data.get('idempotency_key')
        )
        booking = create_booking(
            customer_name=data['customer_name'],
            phone=data['phone'],
            city=data['city'],
            scheduled_at=data['scheduled_at'],
            service_key=data.get('service_key') or None,
            conversation_id=data.get('conversation_id'),
            diagnosis_id=data.get('diagnosis_id'),
            idempotency_key=idempotency_key,
            notes=data.get('notes') or "",
        )

        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="Get Booking Details",
        description="Retrieves a mechanic visit booking by UUID.",
        responses={
            200: BookingSerializer,
            404: OpenApiResponse(description="Booking not found"),
        },
    )
    def get(self, request, pk, *args, **kwargs):
        try:
            booking = Booking.objects.select_related('service', 'mechanic').get(pk=pk)
        except Booking.DoesNotExist:
            raise ApiException(
                code="not_found",
                message="Booking not found.",
                status_code=status.HTTP_404_NOT_FOUND,
            )
        return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)

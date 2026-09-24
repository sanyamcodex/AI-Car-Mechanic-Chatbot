from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from apps.chat.models import Conversation, Message
from apps.diagnosis.models import Diagnosis
from apps.booking.models import Booking
from apps.core.models import AIUsageLog
from apps.core.throttles import AnonRateThrottle


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    @extend_schema(
        summary="Service Health Check",
        description="Returns current service health and database availability status.",
        responses={
            200: inline_serializer(
                name="HealthResponse",
                fields={
                    'status': serializers.CharField(),
                    'db': serializers.BooleanField(),
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.fetchone()
        except Exception:
            db_ok = False

        status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        payload = {
            'status': 'ok' if db_ok else 'degraded',
            'db': db_ok,
        }
        return Response(payload, status=status_code)


class StatsView(APIView):
    throttle_classes = [AnonRateThrottle]

    @extend_schema(
        summary="System and Telemetry Stats",
        description="Returns aggregate usage metrics, diagnoses counts, booking volume, and AI telemetry.",
        responses={
            200: inline_serializer(
                name="StatsResponse",
                fields={
                    'conversations': serializers.IntegerField(),
                    'messages_total': serializers.IntegerField(),
                    'bot_messages_total': serializers.IntegerField(),
                    'diagnoses': serializers.IntegerField(),
                    'bookings': serializers.IntegerField(),
                    'ai_calls_total': serializers.IntegerField(),
                    'ai_cache_hits': serializers.IntegerField(),
                    'ai_failures': serializers.IntegerField(),
                    'ai_call_ratio': serializers.FloatField(),
                    'by_purpose': serializers.DictField(),
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        conv_count = Conversation.objects.count()
        msgs_total = Message.objects.count()
        bot_msgs_total = Message.objects.filter(sender='bot').count()
        diag_count = Diagnosis.objects.count()
        booking_count = Booking.objects.count()

        ai_total = AIUsageLog.objects.count()
        ai_cache_hits = AIUsageLog.objects.filter(cache_hit=True).count()
        ai_failures = AIUsageLog.objects.filter(success=False).count()

        ratio = round(ai_total / max(1, bot_msgs_total), 4)

        by_purpose = {
            'media_image': AIUsageLog.objects.filter(purpose='media_image').count(),
            'media_audio': AIUsageLog.objects.filter(purpose='media_audio').count(),
            'media_video': AIUsageLog.objects.filter(purpose='media_video').count(),
            'extract_text': AIUsageLog.objects.filter(purpose='extract_text').count(),
        }

        return Response({
            'conversations': conv_count,
            'messages_total': msgs_total,
            'bot_messages_total': bot_msgs_total,
            'diagnoses': diag_count,
            'bookings': booking_count,
            'ai_calls_total': ai_total,
            'ai_cache_hits': ai_cache_hits,
            'ai_failures': ai_failures,
            'ai_call_ratio': ratio,
            'by_purpose': by_purpose,
        }, status=status.HTTP_200_OK)


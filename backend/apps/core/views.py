from django.db import connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers


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

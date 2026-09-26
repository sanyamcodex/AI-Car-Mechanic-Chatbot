from typing import Any
from rest_framework import serializers
from apps.booking.models import Booking


class BookingSerializer(serializers.ModelSerializer):
    service = serializers.SerializerMethodField()
    mechanic = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id',
            'customer_name',
            'phone',
            'city',
            'service',
            'mechanic',
            'scheduled_at',
            'status',
            'conversation_id',
            'diagnosis_id',
            'notes',
            'created_at',
            'updated_at',
        ]

    def get_service(self, obj: Booking) -> dict[str, Any]:
        svc = obj.service
        return {
            'key': svc.key,
            'name': svc.name,
            'description': svc.description,
            'price_min': svc.price_min,
            'price_max': svc.price_max,
            'duration_hours': svc.duration_hours,
            'currency': 'INR',
        }

    def get_mechanic(self, obj: Booking) -> dict[str, Any]:
        mech = obj.mechanic
        return {
            'id': mech.id,
            'name': mech.name,
            'city': mech.city,
            'phone': mech.phone,
        }


class BookingCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=60, required=True)
    phone = serializers.CharField(max_length=20, required=True)
    city = serializers.CharField(max_length=64, required=True)
    scheduled_at = serializers.DateTimeField(required=True)
    service_key = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    conversation_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    diagnosis_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=64, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=300, default="")

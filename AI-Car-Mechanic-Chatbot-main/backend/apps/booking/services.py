from datetime import datetime, timedelta, time
from typing import Any
from uuid import UUID
from dateutil import parser as date_parser
from django.db import transaction, IntegrityError
from django.utils import timezone

from apps.booking.models import Booking
from apps.kb.models import Mechanic, ServiceCatalog
from apps.chat.models import Conversation
from apps.diagnosis.models import Diagnosis
from apps.core.errors import ApiException
from engine.extract import parse_phone
from apps.chat.services import apply_event, persist_bot_messages
from engine.types import Event


def find_next_available_slots(city: str, base_time: datetime, count: int = 3) -> list[str]:
    active_mechanics = list(Mechanic.objects.filter(city__iexact=city, active=True))
    if not active_mechanics:
        return []

    now = timezone.now()
    slots: list[str] = []
    check_time = base_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

    # Search up to 14 days ahead
    max_search = now + timedelta(days=14)

    while len(slots) < count and check_time < max_search:
        # Check business hours 9 AM - 6 PM
        if 9 <= check_time.hour <= 18 and check_time >= now + timedelta(hours=2):
            booked_count = Booking.objects.filter(
                mechanic__in=active_mechanics,
                scheduled_at=check_time,
            ).exclude(status='cancelled').count()

            if booked_count < len(active_mechanics):
                slots.append(check_time.isoformat())

        check_time += timedelta(hours=1)
        if check_time.hour > 18:
            # Advance to next day 9 AM
            next_day = check_time.date() + timedelta(days=1)
            check_time = datetime.combine(next_day, time(9, 0), tzinfo=check_time.tzinfo)

    return slots


def create_booking(
    customer_name: str,
    phone: str,
    city: str,
    scheduled_at: str | datetime,
    service_key: str | None = None,
    conversation_id: UUID | str | None = None,
    diagnosis_id: UUID | str | None = None,
    idempotency_key: str | None = None,
    skip_chat_persist: bool = False,
    notes: str = "",
) -> Booking:
    now = timezone.now()

    # 1. Idempotency Check
    if idempotency_key:
        existing = Booking.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return existing

    # 2. Customer Name Validation
    cleaned_name = (customer_name or "").strip()
    if len(cleaned_name) < 2 or len(cleaned_name) > 60:
        raise ApiException(
            code="invalid_name",
            message="Customer name must be between 2 and 60 characters.",
            status_code=400,
        )

    # 3. Phone Validation
    cleaned_phone = parse_phone(phone or "")
    if not cleaned_phone:
        raise ApiException(
            code="invalid_phone",
            message="Please provide a valid 10-digit Indian phone number.",
            status_code=400,
        )

    # 4. City & Mechanic Availability
    cleaned_city = (city or "").strip()
    city_mechanics = list(Mechanic.objects.filter(city__iexact=cleaned_city, active=True))
    if not city_mechanics:
        raise ApiException(
            code="no_mechanic_available",
            message=f"No certified mechanics are currently available in '{cleaned_city}'.",
            status_code=400,
        )
    # Standardize city display name from mechanics list
    canonical_city = city_mechanics[0].city

    # 5. Scheduled_at Validation
    if isinstance(scheduled_at, str):
        try:
            parsed_dt = date_parser.parse(scheduled_at)
        except Exception:
            raise ApiException(
                code="invalid_time_slot",
                message="Invalid datetime format for scheduled_at.",
                status_code=400,
            )
    else:
        parsed_dt = scheduled_at

    if parsed_dt.tzinfo is None:
        parsed_dt = parsed_dt.replace(tzinfo=now.tzinfo)

    # Must be hourly (minutes and seconds == 0)
    if parsed_dt.minute != 0 or parsed_dt.second != 0 or parsed_dt.microsecond != 0:
        raise ApiException(
            code="invalid_time_slot",
            message="Appointments must be scheduled on the hour (e.g. 10:00, 14:00).",
            status_code=400,
        )

    # Business hours: 09:00 - 18:00
    if parsed_dt.hour < 9 or parsed_dt.hour > 18:
        raise ApiException(
            code="invalid_time_slot",
            message="Appointments must be scheduled within business hours (9 AM to 6 PM).",
            status_code=400,
        )

    # At least 2 hours in advance
    if parsed_dt < now + timedelta(hours=2):
        raise ApiException(
            code="invalid_time_slot",
            message="Appointments must be booked at least 2 hours in advance.",
            status_code=400,
        )

    # Max 30 days in advance
    if parsed_dt > now + timedelta(days=30):
        raise ApiException(
            code="invalid_time_slot",
            message="Appointments cannot be booked more than 30 days in advance.",
            status_code=400,
        )

    # 6. Service Resolution
    service_obj: ServiceCatalog | None = None
    if service_key:
        try:
            service_obj = ServiceCatalog.objects.get(key=service_key)
        except ServiceCatalog.DoesNotExist:
            raise ApiException(
                code="invalid_service",
                message=f"Service '{service_key}' not found in catalog.",
                status_code=400,
            )

    conv_obj: Conversation | None = None
    diag_obj: Diagnosis | None = None

    if diagnosis_id:
        diag_obj = Diagnosis.objects.select_related('top_cause__service').filter(id=diagnosis_id).first()
        if diag_obj and not service_obj:
            service_obj = diag_obj.top_cause.service
        if diag_obj and not conversation_id:
            conversation_id = diag_obj.conversation_id

    if conversation_id:
        try:
            conv_obj = Conversation.objects.get(id=conversation_id)
            if not diag_obj:
                diag_id = conv_obj.slots.get("last_diagnosis_id")
                if diag_id:
                    diag_obj = Diagnosis.objects.filter(id=diag_id).first()
            if not diag_obj:
                diag_obj = conv_obj.diagnoses.order_by('-created_at').first()

            if not service_obj and diag_obj:
                service_obj = diag_obj.top_cause.service
        except Conversation.DoesNotExist:
            pass

    if not service_obj:
        # Fallback to general vehicle service
        service_obj = ServiceCatalog.objects.filter(key="electrical_diagnostic_service").first()
        if not service_obj:
            service_obj = ServiceCatalog.objects.first()

    # 7. Mechanic Assignment & Conflict Handling
    try:
        with transaction.atomic():
            # Check available mechanics
            booked_mech_ids = set(
                Booking.objects.filter(
                    mechanic__in=city_mechanics,
                    scheduled_at=parsed_dt,
                ).exclude(status='cancelled').values_list('mechanic_id', flat=True)
            )

            available_mechanics = [m for m in city_mechanics if m.id not in booked_mech_ids]

            if not available_mechanics:
                alternatives = find_next_available_slots(cleaned_city, parsed_dt, count=3)
                raise ApiException(
                    code="slot_unavailable",
                    message="No mechanic is available at the requested time slot.",
                    status_code=409,
                    details={"alternatives": alternatives},
                )

            chosen_mechanic = available_mechanics[0]

            booking = Booking.objects.create(
                conversation=conv_obj,
                diagnosis=diag_obj,
                customer_name=cleaned_name,
                phone=cleaned_phone,
                city=canonical_city,
                service=service_obj,
                mechanic=chosen_mechanic,
                scheduled_at=parsed_dt,
                notes=(notes or "")[:300],
                status='confirmed',
                idempotency_key=idempotency_key or None,
            )

    except IntegrityError:
        alternatives = find_next_available_slots(cleaned_city, parsed_dt, count=3)
        raise ApiException(
            code="slot_unavailable",
            message="No mechanic is available at the requested time slot.",
            status_code=409,
            details={"alternatives": alternatives},
        )

    if conv_obj and not skip_chat_persist:
        booking_data = {
            "id": str(booking.id),
            "service": {"name": service_obj.name},
            "mechanic": {"name": chosen_mechanic.name},
            "scheduled_at": parsed_dt.strftime("%b %d at %I:%M %p"),
        }
        step_result, _ = apply_event(conv_obj, Event(booking_created=booking_data))
        persist_bot_messages(conv_obj, step_result)
        conv_obj.status = 'completed'
        conv_obj.slots = step_result.state.to_dict()
        conv_obj.save(update_fields=['status', 'slots', 'updated_at'])

    return booking

from datetime import datetime, timedelta, timezone
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.booking.models import Booking
from apps.chat.models import Conversation
from apps.kb.management.commands.seed_kb import Command as SeedCommand

IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture(autouse=True)
def seed_database(db):
    SeedCommand().handle()


def _valid_future_time(hours_ahead=5) -> str:
    # Must be on the hour and within business hours (09:00 - 18:00)
    now = datetime.now(IST)
    target = (now + timedelta(hours=hours_ahead)).replace(minute=0, second=0, microsecond=0)
    if target.hour < 9:
        target = target.replace(hour=10)
    elif target.hour > 18:
        target = (target + timedelta(days=1)).replace(hour=11)
    return target.isoformat()


@pytest.mark.django_db
def test_booking_validation_errors():
    client = APIClient()
    url = reverse('booking')
    valid_time = _valid_future_time()

    # 1. Name too short
    r_name = client.post(url, {
        "customer_name": "A",
        "phone": "9812345670",
        "city": "Meerut",
        "scheduled_at": valid_time,
    }, format='json')
    assert r_name.status_code == 400
    assert r_name.json()["error"]["code"] == "invalid_name"

    # 2. Invalid phone
    r_phone = client.post(url, {
        "customer_name": "Rohan Gupta",
        "phone": "12345",
        "city": "Meerut",
        "scheduled_at": valid_time,
    }, format='json')
    assert r_phone.status_code == 400
    assert r_phone.json()["error"]["code"] == "invalid_phone"

    # 3. No mechanic available in city
    r_city = client.post(url, {
        "customer_name": "Rohan Gupta",
        "phone": "9812345670",
        "city": "NonExistentCity",
        "scheduled_at": valid_time,
    }, format='json')
    assert r_city.status_code == 400
    assert r_city.json()["error"]["code"] == "no_mechanic_available"


@pytest.mark.django_db
def test_booking_time_validation_rules():
    client = APIClient()
    url = reverse('booking')
    now = datetime.now(IST)

    # 1. Non-hourly slot (e.g. 10:15)
    non_hourly = (now + timedelta(days=1)).replace(hour=10, minute=15, second=0, microsecond=0).isoformat()
    r1 = client.post(url, {
        "customer_name": "Rohan Gupta",
        "phone": "9812345670",
        "city": "Meerut",
        "scheduled_at": non_hourly,
    }, format='json')
    assert r1.status_code == 400
    assert r1.json()["error"]["code"] == "invalid_time_slot"

    # 2. Off-hours (e.g. 8:00 PM)
    off_hours = (now + timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0).isoformat()
    r2 = client.post(url, {
        "customer_name": "Rohan Gupta",
        "phone": "9812345670",
        "city": "Meerut",
        "scheduled_at": off_hours,
    }, format='json')
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "invalid_time_slot"

    # 3. Past time
    past_time = (now - timedelta(hours=3)).replace(minute=0, second=0, microsecond=0).isoformat()
    r3 = client.post(url, {
        "customer_name": "Rohan Gupta",
        "phone": "9812345670",
        "city": "Meerut",
        "scheduled_at": past_time,
    }, format='json')
    assert r3.status_code == 400
    assert r3.json()["error"]["code"] == "invalid_time_slot"

    # 4. Too far in future (> 30 days)
    far_future = (now + timedelta(days=35)).replace(hour=11, minute=0, second=0, microsecond=0).isoformat()
    r4 = client.post(url, {
        "customer_name": "Rohan Gupta",
        "phone": "9812345670",
        "city": "Meerut",
        "scheduled_at": far_future,
    }, format='json')
    assert r4.status_code == 400
    assert r4.json()["error"]["code"] == "invalid_time_slot"


@pytest.mark.django_db
def test_conflict_409_with_alternatives_when_all_mechanics_booked():
    client = APIClient()
    url = reverse('booking')
    slot_time = _valid_future_time(hours_ahead=10)

    # Meerut has 2 mechanics seeded: Rajesh Kumar and Amit Sharma
    # 1st booking: succeeds (assigned Rajesh Kumar)
    r1 = client.post(url, {
        "customer_name": "Customer One",
        "phone": "9812345671",
        "city": "Meerut",
        "scheduled_at": slot_time,
    }, format='json')
    assert r1.status_code == 201

    # 2nd booking at same slot: succeeds (assigned Amit Sharma)
    r2 = client.post(url, {
        "customer_name": "Customer Two",
        "phone": "9812345672",
        "city": "Meerut",
        "scheduled_at": slot_time,
    }, format='json')
    assert r2.status_code == 201

    # 3rd booking at same slot: must return 409 Conflict with alternative slots!
    r3 = client.post(url, {
        "customer_name": "Customer Three",
        "phone": "9812345673",
        "city": "Meerut",
        "scheduled_at": slot_time,
    }, format='json')
    assert r3.status_code == 409
    data = r3.json()
    assert data["error"]["code"] == "slot_unavailable"
    assert "alternatives" in data["error"]["details"]
    assert len(data["error"]["details"]["alternatives"]) > 0


@pytest.mark.django_db
def test_idempotent_replay():
    client = APIClient()
    url = reverse('booking')
    slot_time = _valid_future_time(hours_ahead=6)

    payload = {
        "customer_name": "Rohan Gupta",
        "phone": "9812345670",
        "city": "Delhi",
        "scheduled_at": slot_time,
        "idempotency_key": "unique-idem-key-8899",
    }

    r1 = client.post(url, payload, format='json')
    assert r1.status_code == 201
    d1 = r1.json()

    # Replay with same idempotency key (header or body)
    r2 = client.post(url, payload, format='json')
    assert r2.status_code == 201
    d2 = r2.json()

    assert d1["id"] == d2["id"]
    assert Booking.objects.filter(idempotency_key="unique-idem-key-8899").count() == 1


@pytest.mark.django_db
def test_booking_get_detail_and_404():
    client = APIClient()
    url = reverse('booking')
    slot_time = _valid_future_time(hours_ahead=7)

    r = client.post(url, {
        "customer_name": "Vikram Malhotra",
        "phone": "9812345673",
        "city": "Noida",
        "scheduled_at": slot_time,
    }, format='json')
    b_id = r.json()["id"]

    detail_url = reverse('booking-detail', kwargs={'pk': b_id})
    res = client.get(detail_url)
    assert res.status_code == 200
    assert res.json()["id"] == b_id

    # Non-existent UUID
    fake_url = reverse('booking-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'})
    res_fake = client.get(fake_url)
    assert res_fake.status_code == 404


@pytest.mark.django_db
def test_booking_via_chat_flow_end_to_end_and_updates_conv_state():
    client = APIClient()
    chat_url = reverse('chat')
    booking_url = reverse('booking')

    # Step 1: Start chat with symptom
    r1 = client.post(chat_url, {
        "choice": {"question_id": "intake", "option_id": "brake_squeal"},
        "client_msg_id": "chat-b-1",
    }, format='json')
    conv_id = r1.json()["conversation_id"]

    # Step 2: Skip vehicle
    r2 = client.post(chat_url, {
        "conversation_id": conv_id,
        "choice": {"question_id": "vehicle", "option_id": "skip"},
        "client_msg_id": "chat-b-2",
    }, format='json')

    # Answer questions to reach diagnosis
    q1 = r2.json()["suggested_replies"][0]
    r3 = client.post(chat_url, {
        "conversation_id": conv_id,
        "choice": {"question_id": q1["question_id"], "option_id": q1["id"]},
        "client_msg_id": "chat-b-3",
    }, format='json')

    q2 = r3.json()["suggested_replies"][0]
    r4 = client.post(chat_url, {
        "conversation_id": conv_id,
        "choice": {"question_id": q2["question_id"], "option_id": q2["id"]},
        "client_msg_id": "chat-b-4",
    }, format='json')

    assert r4.json()["diagnosis"] is not None

    # Step 3: Book via REST API linking conversation_id
    slot_time = _valid_future_time(hours_ahead=8)
    r_book = client.post(booking_url, {
        "conversation_id": conv_id,
        "customer_name": "Amit Sharma",
        "phone": "9812345672",
        "city": "Delhi",
        "scheduled_at": slot_time,
    }, format='json')
    assert r_book.status_code == 201

    # Check conversation state is completed and has confirmation message
    conv = Conversation.objects.get(id=conv_id)
    assert conv.status == "completed"
    assert conv.slots["state"] == "BOOKING_CONFIRMED"
    last_msg = conv.messages.last()
    assert last_msg.kind == "booking"
    assert "confirmed" in last_msg.text.lower()

from typing import Any

STARTER_CHIPS = [
    {"id": "engine_no_crank", "label": "Car won't start", "question_id": "intake"},
    {"id": "brake_squeal", "label": "Brake noise", "question_id": "intake"},
    {"id": "overheating", "label": "Overheating", "question_id": "intake"},
    {"id": "check_engine_light", "label": "Warning light on", "question_id": "intake"},
    {"id": "vibration_speed", "label": "Vibration / shaking", "question_id": "intake"},
    {"id": "ac_not_cooling", "label": "AC not cooling", "question_id": "intake"},
]

OFF_TOPIC_TEXT = (
    "I'm a car mechanic assistant, so I can only help with vehicle and mechanical problems. "
    "Tell me what your car is doing, or pick one below."
)

GREETING_TEXT = (
    "Hello! I'm your virtual mechanic assistant. What seems to be the problem with your vehicle? "
    "Describe the symptoms or pick one of the common issues below."
)

VEHICLE_QUESTION_TEXT = (
    "Could you share your vehicle's make, model, and year? "
    "Knowing your car helps provide more accurate diagnostic suggestions."
)

AI_EXTRACT_FAILED_TEXT = (
    "I couldn't identify the exact vehicle issue from that description. "
    "Could you describe the symptom in more detail or choose from the options below?"
)

MEDIA_ANALYZED_TEXT = (
    "I've examined the media you uploaded: {observations}."
)

UNMATCHED_REPLY_TEXT = "Could you pick one of these?"

FRIENDLY_CLOSE_TEXT = (
    "No problem. Let me know whenever you'd like to troubleshoot another vehicle issue."
)

BOOKING_OFFER_CHIPS = [
    {"id": "yes", "label": "Yes, book a mechanic", "question_id": "book_offer"},
    {"id": "no", "label": "Not now", "question_id": "book_offer"},
]


def format_diagnosis_text(
    top_label: str,
    confidence: float,
    description: str,
    service_name: str,
    price_min: int,
    price_max: int,
    duration_hours: float,
    vehicle: dict[str, Any] | None = None,
) -> str:
    vehicle_str = ""
    if vehicle and (vehicle.get("make") or vehicle.get("model")):
        make = vehicle.get("make", "")
        model = vehicle.get("model", "")
        vehicle_str = f" for your {make} {model}".strip()

    pct = int(round(confidence * 100))
    duration_str = f"{int(duration_hours)}" if duration_hours.is_integer() else f"{duration_hours}"

    return (
        f"Based on what you've told me{vehicle_str}, the most likely cause is **{top_label}** ({pct}% confidence). "
        f"{description} Recommended: **{service_name}** — est. ₹{price_min}–₹{price_max}, about {duration_str}h "
        f"(final quote after inspection). Want me to book a mechanic?"
    )


def format_booking_confirmation(booking: dict[str, Any]) -> str:
    b_id = booking.get("id", "BK-NEW")
    short_id = str(b_id)[:8].upper()
    svc = booking.get("service", {}).get("name", "Vehicle Service")
    mech = booking.get("mechanic", {}).get("name", "our technician") if booking.get("mechanic") else "our technician"
    sched = booking.get("scheduled_at", "scheduled time")

    return (
        f"Your booking has been confirmed (Booking ID: **{short_id}**). "
        f"Service: **{svc}**. Assigned mechanic: **{mech}** for **{sched}**. "
        f"Our mechanic will call you to confirm before heading over."
    )

from datetime import datetime, timedelta, time
from typing import Any
from apps.kb.loader import KB
from engine.types import ConvState, Event, StepResult
from engine.domain_gate import gate, detect_intent
from engine.extract import extract_symptoms, extract_vehicle, parse_phone, parse_when
from engine.scoring import rank, next_question, is_conclusive, build_diagnosis
from engine.safety import red_flags, format_safety_prefix
from engine.templates import (
    STARTER_CHIPS,
    OFF_TOPIC_TEXT,
    GREETING_TEXT,
    VEHICLE_QUESTION_TEXT,
    AI_EXTRACT_FAILED_TEXT,
    MEDIA_ANALYZED_TEXT,
    UNMATCHED_REPLY_TEXT,
    FRIENDLY_CLOSE_TEXT,
    BOOKING_OFFER_CHIPS,
    format_diagnosis_text,
    format_booking_confirmation,
)

MEDIA_FAILED_TEXT = "I couldn't process the media file right now. Could you describe what you're seeing or hearing?"


def _compute_available_slots(now: datetime) -> list[dict[str, str]]:
    slots: list[dict[str, str]] = []
    base = now.date() + timedelta(days=1)
    slot_hours = [10, 14]
    for h in slot_hours:
        dt = datetime.combine(base, time(h, 0), tzinfo=now.tzinfo)
        iso = dt.isoformat()
        label = dt.strftime("%b %d at %I:%M %p")
        slots.append({"id": iso, "label": label, "question_id": "slot"})

    next_base = base + timedelta(days=1)
    dt3 = datetime.combine(next_base, time(11, 0), tzinfo=now.tzinfo)
    slots.append({"id": dt3.isoformat(), "label": dt3.strftime("%b %d at %I:%M %p"), "question_id": "slot"})
    return slots


def _apply_safety(state: ConvState, kb: KB, messages: list[dict[str, Any]]) -> None:
    if state.safety_shown:
        return
    flags = red_flags(kb, state.symptoms)
    if flags and messages:
        prefix = format_safety_prefix(flags[0])
        messages[0]["text"] = prefix + messages[0]["text"]
        state.safety_shown = True


def step(kb: KB, state: ConvState, event: Event, now: datetime) -> StepResult:
    # 1. Booking created event (any state)
    if event.booking_created:
        state.state = "BOOKING_CONFIRMED"
        conf_text = format_booking_confirmation(event.booking_created)
        messages = [{
            "kind": "booking",
            "text": conf_text,
            "meta": {"booking": event.booking_created},
        }]
        return StepResult(state=state, messages=messages, replies=[])

    # 2. Booking error event
    if event.booking_error:
        err = event.booking_error
        err_msg = err.get("message", "We encountered an issue creating your booking.")
        alternatives = err.get("alternatives", [])
        state.state = "BOOKING_DETAILS"
        state.pending_field = "scheduled_at"
        state.draft.pop("scheduled_at", None)

        replies: list[dict[str, str]] = []
        if alternatives:
            for alt in alternatives[:3]:
                try:
                    dt = datetime.fromisoformat(alt)
                    label = dt.strftime("%b %d, %I:%M %p")
                except Exception:
                    label = str(alt)
                replies.append({"id": str(alt), "label": label, "question_id": "slot"})
        else:
            replies = _compute_available_slots(now)

        messages = [{
            "kind": "text",
            "text": f"{err_msg} Please select one of the following available slots:",
            "meta": {},
        }]
        return StepResult(state=state, messages=messages, replies=replies)

    # 3. Media analysis event
    media_messages: list[dict[str, Any]] = []
    if event.media is not None:
        if len(event.media) == 0:
            media_messages.append({
                "kind": "text",
                "text": MEDIA_FAILED_TEXT,
                "meta": {},
            })
        else:
            state.media_analyses += len(event.media)
            for item in event.media:
                syms = item.get("symptom_keys", [])
                for s in syms:
                    if s in kb.symptoms and s not in state.symptoms:
                        state.symptoms.append(s)
                obs = item.get("observations")
                if obs:
                    media_messages.append({
                        "kind": "text",
                        "text": MEDIA_ANALYZED_TEXT.format(observations=obs),
                        "meta": {},
                    })
            if state.state == "INTAKE" and state.symptoms:
                state.state = "CLARIFYING"

    # 4. AI symptoms fallback result
    if event.ai_symptoms is not None:
        valid_keys = [k for k in event.ai_symptoms if k in kb.symptoms]
        if not valid_keys:
            messages = media_messages + [{
                "kind": "text",
                "text": AI_EXTRACT_FAILED_TEXT,
                "meta": {},
            }]
            return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)
        for k in valid_keys:
            if k not in state.symptoms:
                state.symptoms.append(k)
        state.state = "CLARIFYING"

    # If state was BOOKING_CONFIRMED, any new message resets to INTAKE
    if state.state == "BOOKING_CONFIRMED":
        state.state = "INTAKE"
        state.symptoms = []
        state.answers = {}
        state.asked = []
        state.pending_q = None
        state.pending_field = None
        state.draft = {}
        state.safety_shown = False

    text = (event.text or "").strip()
    choice = event.choice or {}

    # ------------------ INTAKE STATE ------------------
    if state.state == "INTAKE":
        if choice.get("question_id") == "intake":
            sym = choice.get("option_id", "")
            if sym in kb.symptoms:
                state.symptoms.append(sym)
                state.state = "CLARIFYING"
            else:
                messages = media_messages + [{"kind": "text", "text": GREETING_TEXT, "meta": {}}]
                return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)
        elif text:
            gate_res = gate(text, kb)
            intent = gate_res["intent"]
            score = gate_res["score"]

            if intent == "greeting":
                messages = media_messages + [{"kind": "text", "text": GREETING_TEXT, "meta": {}}]
                return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)

            if score == 0:
                messages = media_messages + [{"kind": "text", "text": OFF_TOPIC_TEXT, "meta": {}}]
                return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)

            extracted = extract_symptoms(text, kb)
            parsed_v = extract_vehicle(text, kb)
            if parsed_v:
                state.vehicle.update(parsed_v)

            if extracted:
                for s in extracted:
                    if s not in state.symptoms:
                        state.symptoms.append(s)
                state.state = "CLARIFYING"
            else:
                if state.ai_extract_calls < 2:
                    state.ai_extract_calls += 1
                    return StepResult(
                        state=state,
                        messages=media_messages,
                        replies=[],
                        actions={"type": "ai_extract", "text": text},
                    )
                else:
                    messages = media_messages + [{"kind": "text", "text": AI_EXTRACT_FAILED_TEXT, "meta": {}}]
                    return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)
        else:
            if not state.symptoms:
                messages = media_messages + [{"kind": "text", "text": GREETING_TEXT, "meta": {}}]
                return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)

    # ------------------ CLARIFYING STATE ------------------
    if state.state == "CLARIFYING":
        if not state.vehicle.get("make") and not state.vehicle_asked and not state.pending_q:
            state.vehicle_asked = True
            messages = media_messages + [{
                "kind": "text",
                "text": VEHICLE_QUESTION_TEXT,
                "meta": {},
            }]
            _apply_safety(state, kb, messages)
            replies = [{"id": "skip", "label": "Skip", "question_id": "vehicle"}]
            return StepResult(state=state, messages=messages, replies=replies)

        if choice.get("question_id") == "vehicle":
            if choice.get("option_id") != "skip" and text:
                parsed_v = extract_vehicle(text, kb)
                if parsed_v:
                    state.vehicle.update(parsed_v)
        elif state.vehicle_asked and not state.pending_q and not state.answers and text:
            parsed_v = extract_vehicle(text, kb)
            if parsed_v:
                state.vehicle.update(parsed_v)
            new_syms = extract_symptoms(text, kb)
            for s in new_syms:
                if s not in state.symptoms:
                    state.symptoms.append(s)

        if state.pending_q:
            q_key = state.pending_q
            curr_q = kb.questions.get(q_key)

            if choice.get("question_id") == q_key:
                opt_id = choice.get("option_id", "")
                if opt_id != "unknown":
                    state.answers[q_key] = opt_id
                state.pending_q = None
            elif text:
                gate_res = gate(text, kb)
                if gate_res["score"] == 0 and gate_res["intent"] not in {"yes", "no", "idk"}:
                    messages = media_messages + [{
                        "kind": "text",
                        "text": f"{OFF_TOPIC_TEXT}\n\n{curr_q.text if curr_q else ''}".strip(),
                        "meta": {},
                    }]
                    replies = [
                        {"id": opt.id, "label": opt.label, "question_id": q_key}
                        for opt in (curr_q.options if curr_q else [])
                    ] + [{"id": "unknown", "label": "Not sure", "question_id": q_key}]
                    return StepResult(state=state, messages=messages, replies=replies)

                matched_opt_id: str | None = None
                normalized_text = text.lower()

                if gate_res["intent"] == "idk":
                    matched_opt_id = "unknown"
                else:
                    for opt in (curr_q.options if curr_q else []):
                        if opt.id.lower() in normalized_text or opt.label.lower() in normalized_text:
                            matched_opt_id = opt.id
                            break
                        for kw in opt.keywords:
                            if kw in normalized_text:
                                matched_opt_id = opt.id
                                break
                        if matched_opt_id:
                            break

                if not matched_opt_id:
                    if gate_res["intent"] == "yes":
                        for opt in (curr_q.options if curr_q else []):
                            if "yes" in opt.id.lower() or "yes" in opt.label.lower():
                                matched_opt_id = opt.id
                                break
                    elif gate_res["intent"] == "no":
                        for opt in (curr_q.options if curr_q else []):
                            if "no" in opt.id.lower() or "no" in opt.label.lower():
                                matched_opt_id = opt.id
                                break

                new_syms = extract_symptoms(text, kb)
                for s in new_syms:
                    if s not in state.symptoms:
                        state.symptoms.append(s)

                if matched_opt_id:
                    if matched_opt_id != "unknown":
                        state.answers[q_key] = matched_opt_id
                    state.pending_q = None
                else:
                    messages = media_messages + [{
                        "kind": "text",
                        "text": f"{UNMATCHED_REPLY_TEXT}\n\n{curr_q.text if curr_q else ''}".strip(),
                        "meta": {},
                    }]
                    replies = [
                        {"id": opt.id, "label": opt.label, "question_id": q_key}
                        for opt in (curr_q.options if curr_q else [])
                    ] + [{"id": "unknown", "label": "Not sure", "question_id": q_key}]
                    return StepResult(state=state, messages=messages, replies=replies)

        ranked = rank(kb, state)
        next_q = next_question(kb, state, ranked)
        conclusive = is_conclusive(state, ranked, next_q)

        if conclusive and ranked:
            diag = build_diagnosis(kb, state, ranked)
            state.state = "BOOKING_OFFERED"
            state.pending_q = None

            top_cause = kb.causes[ranked[0].cause_key]
            svc = kb.services[top_cause.service_key]
            diag_text = format_diagnosis_text(
                top_label=top_cause.label,
                confidence=ranked[0].confidence,
                description=top_cause.description,
                service_name=svc.name,
                price_min=svc.price_min,
                price_max=svc.price_max,
                duration_hours=svc.duration_hours,
                vehicle=state.vehicle,
            )

            messages = media_messages + [{
                "kind": "diagnosis",
                "text": diag_text,
                "meta": {
                    "diagnosis": {
                        "id": diag.evidence_hash[:8],
                        "top": diag.top,
                        "ranked": diag.ranked,
                        "severity": diag.severity,
                        "safety_alert": diag.safety_alert,
                        "service": diag.service,
                    }
                },
            }]
            _apply_safety(state, kb, messages)
            return StepResult(
                state=state,
                messages=messages,
                replies=BOOKING_OFFER_CHIPS,
                diagnosis=diag,
            )

        if next_q:
            state.pending_q = next_q.key
            state.asked.append(next_q.key)
            replies = [
                {"id": opt.id, "label": opt.label, "question_id": next_q.key}
                for opt in next_q.options
            ] + [{"id": "unknown", "label": "Not sure", "question_id": next_q.key}]

            messages = media_messages + [{
                "kind": "text",
                "text": next_q.text,
                "meta": {},
            }]
            _apply_safety(state, kb, messages)
            return StepResult(state=state, messages=messages, replies=replies)

    # ------------------ BOOKING_OFFERED STATE ------------------
    if state.state == "BOOKING_OFFERED":
        intent = detect_intent(text) if text else "other"

        if (choice.get("question_id") == "book_offer" and choice.get("option_id") == "yes") or intent == "yes":
            state.state = "BOOKING_DETAILS"
            state.pending_field = "customer_name"
            messages = [{
                "kind": "text",
                "text": "Great! Who should the mechanic ask for? Please enter your full name.",
                "meta": {},
            }]
            return StepResult(state=state, messages=messages, replies=[])

        if (choice.get("question_id") == "book_offer" and choice.get("option_id") == "no") or intent in {"no", "restart"}:
            state.state = "INTAKE"
            state.symptoms = []
            state.answers = {}
            state.asked = []
            state.pending_q = None
            state.pending_field = None
            state.draft = {}
            messages = [{"kind": "text", "text": FRIENDLY_CLOSE_TEXT, "meta": {}}]
            return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)

        new_syms = extract_symptoms(text, kb)
        if new_syms:
            state.state = "CLARIFYING"
            state.symptoms = new_syms
            state.answers = {}
            state.asked = []
            state.pending_q = None
            state.pending_field = None
            return step(kb, state, Event(), now)

        messages = [{
            "kind": "text",
            "text": f"{OFF_TOPIC_TEXT}\n\nWould you like to book a certified mechanic for this service?",
            "meta": {},
        }]
        return StepResult(state=state, messages=messages, replies=BOOKING_OFFER_CHIPS)

    # ------------------ BOOKING_DETAILS STATE ------------------
    if state.state == "BOOKING_DETAILS":
        intent = detect_intent(text) if text else "other"
        if intent in {"no", "restart"} or text.lower() in {"cancel", "stop", "exit"}:
            state.state = "INTAKE"
            state.symptoms = []
            state.answers = {}
            state.asked = []
            state.pending_q = None
            state.pending_field = None
            state.draft = {}
            messages = [{"kind": "text", "text": FRIENDLY_CLOSE_TEXT, "meta": {}}]
            return StepResult(state=state, messages=messages, replies=STARTER_CHIPS)

        if state.pending_field == "customer_name":
            if text and 2 <= len(text.strip()) <= 60:
                state.draft["customer_name"] = text.strip()
                p = parse_phone(text)
                if p:
                    state.draft["phone"] = p
                    state.pending_field = "city"
                    messages = [{
                        "kind": "text",
                        "text": f"Thanks, {state.draft['customer_name']}. Which city are you located in?",
                        "meta": {},
                    }]
                    replies = [
                        {"id": "Meerut", "label": "Meerut", "question_id": "city"},
                        {"id": "Delhi", "label": "Delhi", "question_id": "city"},
                        {"id": "Noida", "label": "Noida", "question_id": "city"},
                        {"id": "Gurugram", "label": "Gurugram", "question_id": "city"},
                        {"id": "Ghaziabad", "label": "Ghaziabad", "question_id": "city"},
                    ]
                    return StepResult(state=state, messages=messages, replies=replies)
                else:
                    state.pending_field = "phone"
                    messages = [{
                        "kind": "text",
                        "text": f"Thanks, {state.draft['customer_name']}. What is your 10-digit mobile number for service updates?",
                        "meta": {},
                    }]
                    return StepResult(state=state, messages=messages, replies=[])
            else:
                messages = [{
                    "kind": "text",
                    "text": "Please provide a valid name (between 2 and 60 characters).",
                    "meta": {},
                }]
                return StepResult(state=state, messages=messages, replies=[])

        if state.pending_field == "phone":
            p = parse_phone(text)
            if p:
                state.draft["phone"] = p
                state.pending_field = "city"
                messages = [{
                    "kind": "text",
                    "text": "Got it. Which city are you located in?",
                    "meta": {},
                }]
                replies = [
                    {"id": "Meerut", "label": "Meerut", "question_id": "city"},
                    {"id": "Delhi", "label": "Delhi", "question_id": "city"},
                    {"id": "Noida", "label": "Noida", "question_id": "city"},
                    {"id": "Gurugram", "label": "Gurugram", "question_id": "city"},
                    {"id": "Ghaziabad", "label": "Ghaziabad", "question_id": "city"},
                ]
                return StepResult(state=state, messages=messages, replies=replies)
            else:
                messages = [{
                    "kind": "text",
                    "text": "Please provide a valid 10-digit Indian phone number (starting with 6-9).",
                    "meta": {},
                }]
                return StepResult(state=state, messages=messages, replies=[])

        if state.pending_field == "city":
            city_val = choice.get("option_id") if choice.get("question_id") == "city" else text
            if city_val and 2 <= len(city_val.strip()) <= 40:
                state.draft["city"] = city_val.strip().title()
                state.pending_field = "scheduled_at"
                slots = _compute_available_slots(now)
                messages = [{
                    "kind": "text",
                    "text": f"Perfect. When should our mechanic visit in {state.draft['city']}? Select a slot or type your preferred date & time.",
                    "meta": {},
                }]
                return StepResult(state=state, messages=messages, replies=slots)
            else:
                messages = [{
                    "kind": "text",
                    "text": "Please provide your city name (e.g., Meerut, Delhi, Noida).",
                    "meta": {},
                }]
                return StepResult(state=state, messages=messages, replies=[])

        if state.pending_field == "scheduled_at":
            chosen_slot: str | None = None
            if choice.get("question_id") == "slot":
                chosen_slot = choice.get("option_id")
            elif text:
                parsed_dt = parse_when(text, now)
                if parsed_dt:
                    chosen_slot = parsed_dt.isoformat()

            if chosen_slot:
                state.draft["scheduled_at"] = chosen_slot
                return StepResult(
                    state=state,
                    messages=[],
                    replies=[],
                    actions={"type": "create_booking", "draft": dict(state.draft)},
                )
            else:
                slots = _compute_available_slots(now)
                messages = [{
                    "kind": "text",
                    "text": "Please choose a slot during business hours (9 AM to 6 PM, at least 2 hours in advance).",
                    "meta": {},
                }]
                return StepResult(state=state, messages=messages, replies=slots)

    return StepResult(state=state, messages=[], replies=STARTER_CHIPS)

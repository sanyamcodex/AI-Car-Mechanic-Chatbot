from datetime import datetime, timedelta, timezone
from apps.kb.loader import load_kb, clear_kb_cache
from engine.types import ConvState, Event
from engine.flow import step
from engine.templates import OFF_TOPIC_TEXT, UNMATCHED_REPLY_TEXT
from tests.engine.fixtures import get_fixture_kb

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 9, 24, 10, 0, tzinfo=IST)


def test_full_happy_path():
    kb = get_fixture_kb()
    state = ConvState()

    # Step 1: Intake symptom selection
    e1 = Event(choice={"question_id": "intake", "option_id": "brake_squeal"})
    r1 = step(kb, state, e1, NOW)
    assert r1.state.state == "CLARIFYING"
    assert "brake_squeal" in r1.state.symptoms
    assert r1.replies[0]["id"] == "skip"

    # Step 2: Skip vehicle question
    e2 = Event(choice={"question_id": "vehicle", "option_id": "skip"})
    r2 = step(kb, r1.state, e2, NOW)
    assert r2.state.state == "CLARIFYING"
    assert r2.state.pending_q is not None
    q1_key = r2.state.pending_q

    # Step 3: Answer Question 1
    e3 = Event(choice={"question_id": q1_key, "option_id": "only_braking"})
    r3 = step(kb, r2.state, e3, NOW)
    assert r3.state.state == "CLARIFYING"
    assert r3.state.answers[q1_key] == "only_braking"
    assert r3.state.pending_q is not None
    q2_key = r3.state.pending_q

    # Step 4: Answer Question 2 (reaches conclusiveness)
    e4 = Event(choice={"question_id": q2_key, "option_id": "normal_effort"})
    r4 = step(kb, r3.state, e4, NOW)
    assert r4.state.state == "BOOKING_OFFERED"
    assert r4.diagnosis is not None
    assert r4.diagnosis.top["cause_key"] == "worn_brake_pads"
    assert any(reply["id"] == "yes" for reply in r4.replies)

    # Step 5: Accept booking offer
    e5 = Event(choice={"question_id": "book_offer", "option_id": "yes"})
    r5 = step(kb, r4.state, e5, NOW)
    assert r5.state.state == "BOOKING_DETAILS"
    assert r5.state.pending_field == "customer_name"

    # Step 6: Provide customer name
    e6 = Event(text="Rohan Gupta")
    r6 = step(kb, r5.state, e6, NOW)
    assert r6.state.state == "BOOKING_DETAILS"
    assert r6.state.draft["customer_name"] == "Rohan Gupta"
    assert r6.state.pending_field == "phone"

    # Step 7: Provide phone number
    e7 = Event(text="9812345670")
    r7 = step(kb, r6.state, e7, NOW)
    assert r7.state.state == "BOOKING_DETAILS"
    assert r7.state.draft["phone"] == "9812345670"
    assert r7.state.pending_field == "city"

    # Step 8: Provide city
    e8 = Event(text="Meerut")
    r8 = step(kb, r7.state, e8, NOW)
    assert r8.state.state == "BOOKING_DETAILS"
    assert r8.state.draft["city"] == "Meerut"
    assert r8.state.pending_field == "scheduled_at"
    assert len(r8.replies) > 0

    # Step 9: Select scheduled time slot -> produces create_booking action
    slot_id = r8.replies[0]["id"]
    e9 = Event(choice={"question_id": "slot", "option_id": slot_id})
    r9 = step(kb, r8.state, e9, NOW)
    assert r9.actions is not None
    assert r9.actions["type"] == "create_booking"
    assert r9.actions["draft"]["scheduled_at"] == slot_id

    # Step 10: Backend reports booking_created
    booking_obj = {
        "id": "BK-99887766",
        "service": {"name": "Brake pad & disc service"},
        "mechanic": {"name": "Rajesh Kumar"},
        "scheduled_at": slot_id,
    }
    e10 = Event(booking_created=booking_obj)
    r10 = step(kb, r9.state, e10, NOW)
    assert r10.state.state == "BOOKING_CONFIRMED"
    assert r10.messages[0]["kind"] == "booking"
    assert "BK-99887766"[:8] in r10.messages[0]["text"]


def test_off_topic_handling_in_states():
    kb = get_fixture_kb()

    # 1. INTAKE off-topic
    s1 = ConvState()
    r1 = step(kb, s1, Event(text="what is the weather today"), NOW)
    assert r1.state.state == "INTAKE"
    assert OFF_TOPIC_TEXT in r1.messages[0]["text"]

    # 2. CLARIFYING off-topic
    s2 = ConvState(state="CLARIFYING", symptoms=["brake_squeal"], pending_q="q_brake_when")
    r2 = step(kb, s2, Event(text="tell me a cooking recipe"), NOW)
    assert s2.state == "CLARIFYING"
    assert OFF_TOPIC_TEXT in r2.messages[0]["text"]
    assert s2.pending_q == "q_brake_when"

    # 3. BOOKING_OFFERED off-topic
    s3 = ConvState(state="BOOKING_OFFERED")
    r3 = step(kb, s3, Event(text="who won the game"), NOW)
    assert r3.state.state == "BOOKING_OFFERED"
    assert OFF_TOPIC_TEXT in r3.messages[0]["text"]


def test_unmatched_answer_reask():
    kb = get_fixture_kb()
    s = ConvState(state="CLARIFYING", symptoms=["brake_squeal"], pending_q="q_brake_when")
    # Unmatched answer (contains car words so not off-topic, but not an option)
    r = step(kb, s, Event(text="mechanic car repair"), NOW)
    assert UNMATCHED_REPLY_TEXT in r.messages[0]["text"]
    assert s.pending_q == "q_brake_when"


def test_red_flag_prefix_shown_once():
    kb = get_fixture_kb()
    s = ConvState(state="INTAKE")

    # Turn 1: trigger red-flag symptom
    r1 = step(kb, s, Event(choice={"question_id": "intake", "option_id": "overheating"}), NOW)
    assert "Safety first:" in r1.messages[0]["text"]
    assert r1.state.safety_shown is True

    # Turn 2: next reply must NOT repeat Safety first
    r2 = step(kb, r1.state, Event(choice={"question_id": "vehicle", "option_id": "skip"}), NOW)
    assert "Safety first:" not in r2.messages[0]["text"]


def test_booking_error_with_alternatives():
    kb = get_fixture_kb()
    s = ConvState(state="BOOKING_DETAILS", pending_field="scheduled_at")
    err_event = Event(booking_error={
        "code": "slot_unavailable",
        "message": "Selected slot is already taken.",
        "alternatives": ["2026-09-25T14:00:00+05:30", "2026-09-25T15:00:00+05:30"]
    })
    r = step(kb, s, err_event, NOW)
    assert r.state.pending_field == "scheduled_at"
    assert len(r.replies) == 2
    assert r.replies[0]["id"] == "2026-09-25T14:00:00+05:30"


def test_determinism():
    kb = get_fixture_kb()
    s1 = ConvState(state="CLARIFYING", symptoms=["brake_squeal"], pending_q="q_brake_when")
    s2 = ConvState(state="CLARIFYING", symptoms=["brake_squeal"], pending_q="q_brake_when")

    e = Event(choice={"question_id": "q_brake_when", "option_id": "only_braking"})
    r1 = step(kb, s1, e, NOW)
    r2 = step(kb, s2, e, NOW)

    assert r1.state.to_dict() == r2.state.to_dict()
    assert r1.messages == r2.messages
    assert r1.replies == r2.replies


def test_golden_scenarios_on_real_kb():
    clear_kb_cache()
    kb = load_kb()
    from engine.scoring import rank

    golden_cases = {
        "brake_squeal": "worn_brake_pads",
        "engine_no_crank": "dead_battery",
        "slow_crank_click": "weak_battery",
        "overheating": "low_coolant",
        "ac_not_cooling": "low_refrigerant",
        "tire_flat": "puncture",
    }

    for sym, expected_cause in golden_cases.items():
        state = ConvState(symptoms=[sym])
        ranked = rank(kb, state)
        assert len(ranked) > 0
        assert ranked[0].cause_key == expected_cause, (
            f"Golden scenario failed: symptom '{sym}' ranked '{ranked[0].cause_key}' instead of '{expected_cause}'"
        )

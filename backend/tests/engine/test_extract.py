from datetime import datetime, timedelta, timezone
from backend.engine.extract import extract_symptoms, extract_vehicle, parse_phone, parse_when
from backend.tests.engine.fixtures import get_fixture_kb

IST = timezone(timedelta(hours=5, minutes=30))


def test_extract_symptoms():
    kb = get_fixture_kb()
    syms = extract_symptoms("I hear a loud squeal and brake noise when stopping", kb)
    assert "brake_squeal" in syms

    overheat_syms = extract_symptoms("my car engine is overheating on the road", kb)
    assert "overheating" in overheat_syms


def test_extract_vehicle():
    kb = get_fixture_kb()
    res1 = extract_vehicle("I drive a 2019 Maruti Swift VXi", kb)
    assert res1.get("year") == 2019
    assert res1.get("make") == "Maruti"
    assert "Swift" in res1.get("model", "")

    res2 = extract_vehicle("Hyundai Creta 2021", kb)
    assert res2.get("year") == 2021
    assert res2.get("make") == "Hyundai"
    assert "Creta" in res2.get("model", "")


def test_parse_phone():
    assert parse_phone("My number is 9812345670") == "9812345670"
    assert parse_phone("+91 9812345670 please call") == "9812345670"
    assert parse_phone("call me at 88888-99999") == "8888899999"
    assert parse_phone("invalid phone 12345") is None


def test_parse_when():
    now = datetime(2026, 9, 24, 10, 0, tzinfo=IST)

    # Valid tomorrow slot at 11 AM
    dt = parse_when("tomorrow at 11:00 am", now)
    assert dt is not None
    assert dt.day == 25
    assert dt.hour == 11
    assert dt.minute == 0

    # Valid day after tomorrow at 3 PM
    dt2 = parse_when("day after tomorrow 3pm", now)
    assert dt2 is not None
    assert dt2.day == 26
    assert dt2.hour == 15

    # Out of business hours (e.g. 8 PM)
    assert parse_when("tomorrow at 8:00 pm", now) is None

    # Too soon (< 2 hours ahead)
    assert parse_when("today at 11:00 am", now) is None

    # Far future (> 30 days)
    assert parse_when("in 40 days at 11:00 am", now) is None

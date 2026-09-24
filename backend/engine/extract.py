import re
from datetime import datetime, timedelta, time
from typing import Any
from dateutil import parser as date_parser
from apps.kb.loader import KB

RE_YEAR = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")
RE_PHONE = re.compile(r"(?:\+?91[\s-]?)?([6-9]\d{9})\b")


def extract_symptoms(text: str, kb: KB) -> list[str]:
    if not text:
        return []

    normalized = re.sub(r"[^\w\s-]", " ", text.lower())
    found_symptoms: list[str] = []
    seen: set[str] = set()

    # Sort keywords by length descending so most specific phrases match first
    sorted_keywords = sorted(kb.symptoms_by_keyword.keys(), key=lambda k: len(k), reverse=True)

    for kw in sorted_keywords:
        pattern = r"\b" + re.escape(kw) + r"\b"
        if re.search(pattern, normalized):
            for sym in kb.symptoms_by_keyword[kw]:
                if sym not in seen:
                    seen.add(sym)
                    found_symptoms.append(sym)

    return found_symptoms


def extract_vehicle(text: str, kb: KB) -> dict[str, Any]:
    if not text:
        return {}

    normalized = text.lower()
    vehicle: dict[str, Any] = {}

    year_match = RE_YEAR.search(normalized)
    if year_match:
        vehicle["year"] = int(year_match.group(1))

    # Look for make
    words = re.findall(r"\b[\w-]+\b", normalized)
    found_make: str | None = None
    make_index: int = -1

    for idx, word in enumerate(words):
        if word in kb.lexicon_makes:
            found_make = word
            make_index = idx
            break

    if found_make:
        vehicle["make"] = found_make.capitalize()
        # Look for model in subsequent 1-2 tokens
        if make_index != -1 and make_index + 1 < len(words):
            candidate_tokens = words[make_index + 1 : make_index + 3]
            # Exclude year tokens from candidate model
            model_tokens = [t for t in candidate_tokens if not RE_YEAR.match(t)]
            if model_tokens:
                vehicle["model"] = " ".join(t.capitalize() for t in model_tokens)

    # If model was not found after make, check if any lexicon_model exists anywhere in the text
    if "model" not in vehicle:
        for word in words:
            if word in kb.lexicon_models:
                vehicle["model"] = word.capitalize()
                break

    return vehicle


def parse_phone(text: str) -> str | None:
    if not text:
        return None
    match = RE_PHONE.search(text.replace(" ", "").replace("-", ""))
    if not match:
        # Also try direct regex on original text with spaces/hyphens allowed
        match = RE_PHONE.search(text)
    if match:
        return match.group(1)
    return None


def parse_when(text: str, now: datetime) -> datetime | None:
    if not text or not text.strip():
        return None

    cleaned = text.strip().lower()
    base_date = now.date()

    # Relative day replacements
    if "day after tomorrow" in cleaned:
        base_date = now.date() + timedelta(days=2)
        cleaned = cleaned.replace("day after tomorrow", "")
    elif "tomorrow" in cleaned:
        base_date = now.date() + timedelta(days=1)
        cleaned = cleaned.replace("tomorrow", "")
    elif "today" in cleaned:
        base_date = now.date()
        cleaned = cleaned.replace("today", "")

    try:
        # Fuzzy parse remaining time/date information
        default_dt = datetime.combine(base_date, time(10, 0), tzinfo=now.tzinfo)
        parsed = date_parser.parse(cleaned, fuzzy=True, default=default_dt)
        if parsed.tzinfo is None and now.tzinfo is not None:
            parsed = parsed.replace(tzinfo=now.tzinfo)

        # Round to whole hour
        if parsed.minute >= 30:
            parsed = parsed + timedelta(hours=1)
        parsed = parsed.replace(minute=0, second=0, microsecond=0)

        # Business hours 09:00 - 18:00 IST
        if parsed.hour < 9 or parsed.hour > 18:
            return None

        # At least 2 hours ahead
        if parsed < now + timedelta(hours=2):
            return None

        # At most 30 days ahead
        if parsed > now + timedelta(days=30):
            return None

        return parsed
    except Exception:
        return None

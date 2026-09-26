import re
from typing import Any
from apps.kb.loader import KB

RE_GREETING = re.compile(r"^(hi|hello|hey|namaste|good (morning|afternoon|evening))\b", re.IGNORECASE)
RE_YES = re.compile(r"^(yes|yeah|yep|sure|ok(ay)?|please|book it|haanji|haan|ha)\b", re.IGNORECASE)
RE_NO = re.compile(r"^(no|nope|nah|not now|later|cancel|nahi)\b", re.IGNORECASE)
RE_IDK = re.compile(r"^(not sure|don'?t know|idk|no idea)", re.IGNORECASE)
RE_RESTART = re.compile(r"(new issue|start over|another problem)", re.IGNORECASE)


def detect_intent(text: str) -> str:
    cleaned = text.strip()
    if RE_GREETING.search(cleaned):
        return "greeting"
    if RE_RESTART.search(cleaned):
        return "restart"
    if RE_YES.search(cleaned):
        return "yes"
    if RE_IDK.search(cleaned):
        return "idk"
    if RE_NO.search(cleaned):
        return "no"
    return "other"


def gate(text: str, kb: KB) -> dict[str, Any]:
    if not text or not text.strip():
        return {"score": 0, "intent": "other"}

    intent = detect_intent(text)

    # Normalize text: lowercase and replace punctuation with spaces
    normalized = re.sub(r"[^\w\s-]", " ", text.lower())
    words = set(re.findall(r"\b[\w-]+\b", normalized))

    matched_hits: set[str] = set()

    # Check words against lexicon terms, makes, models
    for word in words:
        if word in kb.lexicon_terms:
            matched_hits.add(word)
        if word in kb.lexicon_makes:
            matched_hits.add(word)
        if word in kb.lexicon_models:
            matched_hits.add(word)

    # Check multi-word symptom keywords and multi-word lexicon terms
    for kw in kb.symptoms_by_keyword.keys():
        kw_clean = kw.strip().lower()
        if " " in kw_clean:
            pattern = r"\b" + re.escape(kw_clean) + r"\b"
            if re.search(pattern, normalized):
                matched_hits.add(kw_clean)
        elif kw_clean in words:
            matched_hits.add(kw_clean)

    for term in kb.lexicon_terms:
        if " " in term:
            pattern = r"\b" + re.escape(term) + r"\b"
            if re.search(pattern, normalized):
                matched_hits.add(term)

    return {
        "score": len(matched_hits),
        "intent": intent,
    }

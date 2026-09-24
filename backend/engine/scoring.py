import hashlib
import json
from typing import Any
from apps.kb.loader import KB, QuestionD
from backend.engine.types import ConvState, Ranked, DiagnosisData


def rank(kb: KB, state: ConvState) -> list[Ranked]:
    if not state.symptoms:
        return []

    # Candidates = causes linked to >= 1 present symptom
    candidate_keys = [
        c_key for c_key, cause in kb.causes.items()
        if any(sym in cause.symptoms for sym in state.symptoms)
    ]

    if not candidate_keys:
        return []

    raw_scores: dict[str, float] = {}
    why_map: dict[str, list[str]] = {}

    for c_key in candidate_keys:
        cause = kb.causes[c_key]
        score = 0.0
        why_items: list[str] = []

        # 1. Symptom weights
        for sym in state.symptoms:
            if sym in cause.symptoms:
                weight = cause.symptoms[sym]
                score += weight
                sym_label = kb.symptoms[sym].label if sym in kb.symptoms else sym
                why_items.append(f"Matches: {sym_label}")

        # 2. Answer effects
        for q_key, opt_id in state.answers.items():
            if q_key in kb.questions:
                q = kb.questions[q_key]
                opt = next((o for o in q.options if o.id == opt_id), None)
                if opt and c_key in opt.effects:
                    delta = opt.effects[c_key]
                    score += delta
                    if delta > 0:
                        why_items.append(f"Your answer '{opt.label}' supports this")
                    elif delta < 0:
                        why_items.append(f"Your answer '{opt.label}' reduces likelihood")

        # Clip negatives to 0
        final_score = max(0.0, score)
        raw_scores[c_key] = final_score
        why_map[c_key] = why_items

    total_positive = sum(raw_scores.values())

    ranked_list: list[Ranked] = []
    for c_key, sc in raw_scores.items():
        conf = (sc / total_positive) if total_positive > 0 else 0.0
        ranked_list.append(
            Ranked(
                cause_key=c_key,
                score=round(sc, 4),
                confidence=round(conf, 4),
                why=why_map[c_key],
            )
        )

    # Sort descending by score, then ascending by cause_key for deterministic ties
    ranked_list.sort(key=lambda r: (-r.score, r.cause_key))
    return ranked_list


def next_question(kb: KB, state: ConvState, ranked: list[Ranked]) -> QuestionD | None:
    if not state.symptoms:
        return None

    # Unanswered and unasked questions whose applies_when intersects symptoms
    candidates: list[QuestionD] = []
    for q_key, q in kb.questions.items():
        if q_key in state.answers or q_key in state.asked:
            continue
        if any(sym in state.symptoms for sym in q.applies_when):
            candidates.append(q)

    if not candidates:
        return None

    if not ranked:
        candidates.sort(key=lambda q: q.key)
        return candidates[0]

    top1 = ranked[0].cause_key
    top2 = ranked[1].cause_key if len(ranked) > 1 else None

    # gain(q) = sum_options |effects[top1] - effects[top2]|
    best_q: QuestionD | None = None
    best_gain: float = -1.0

    for q in sorted(candidates, key=lambda x: x.key):
        gain = 0.0
        for opt in q.options:
            e1 = opt.effects.get(top1, 0.0)
            e2 = opt.effects.get(top2, 0.0) if top2 else 0.0
            gain += abs(e1 - e2)

        if gain > best_gain:
            best_gain = gain
            best_q = q

    return best_q


def is_conclusive(state: ConvState, ranked: list[Ranked], next_q: QuestionD | None) -> bool:
    if not ranked:
        return False

    answered = len(state.answers)
    if answered >= 5:
        return True
    if next_q is None:
        return True

    if answered >= 2:
        top = ranked[0]
        second = ranked[1] if len(ranked) > 1 else None
        margin = (top.confidence - second.confidence) if second else top.confidence
        if top.confidence >= 0.5 and margin >= 0.15:
            return True

    return False


def build_diagnosis(kb: KB, state: ConvState, ranked: list[Ranked]) -> DiagnosisData:
    top_ranked = ranked[0]
    top_cause = kb.causes[top_ranked.cause_key]

    # Top 3 ranked causes
    top_3_ranked = [
        {
            "cause_key": r.cause_key,
            "label": kb.causes[r.cause_key].label if r.cause_key in kb.causes else r.cause_key,
            "confidence": r.confidence,
            "why": r.why,
        }
        for r in ranked[:3]
    ]

    # Severity: max cause severity among top 2
    top_2_severities = [
        kb.causes[r.cause_key].severity for r in ranked[:2]
        if r.cause_key in kb.causes
    ]
    severity = max(top_2_severities) if top_2_severities else 2

    # Safety alert: first red-flag symptom's safety_msg in state.symptoms
    safety_alert: str | None = None
    for sym in state.symptoms:
        if sym in kb.symptoms and kb.symptoms[sym].red_flag and kb.symptoms[sym].safety_msg:
            safety_alert = kb.symptoms[sym].safety_msg
            break

    # Service catalog details
    service_obj = kb.services[top_cause.service_key]
    service_dict = {
        "key": service_obj.key,
        "name": service_obj.name,
        "description": service_obj.description,
        "price_min": service_obj.price_min,
        "price_max": service_obj.price_max,
        "currency": "INR",
        "duration_hours": service_obj.duration_hours,
    }

    # Evidence hash = sha1 of sorted symptoms + sorted answers
    evidence_payload = {
        "symptoms": sorted(state.symptoms),
        "answers": sorted(state.answers.items()),
    }
    evidence_str = json.dumps(evidence_payload, sort_keys=True)
    evidence_hash = hashlib.sha1(evidence_str.encode("utf-8")).hexdigest()

    return DiagnosisData(
        top={
            "cause_key": top_cause.key,
            "label": top_cause.label,
            "description": top_cause.description,
            "confidence": top_ranked.confidence,
        },
        ranked=top_3_ranked,
        severity=severity,
        safety_alert=safety_alert,
        service=service_dict,
        evidence_hash=evidence_hash,
    )

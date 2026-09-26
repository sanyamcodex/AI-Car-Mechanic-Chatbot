from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConvState:
    state: str = "INTAKE"
    vehicle: dict[str, Any] = field(default_factory=dict)
    vehicle_asked: bool = False
    symptoms: list[str] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)
    asked: list[str] = field(default_factory=list)
    pending_q: str | None = None
    pending_field: str | None = None
    ai_extract_calls: int = 0
    media_analyses: int = 0
    draft: dict[str, Any] = field(default_factory=dict)
    last_diagnosis_id: str | None = None
    safety_shown: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "vehicle": dict(self.vehicle),
            "vehicle_asked": self.vehicle_asked,
            "symptoms": list(self.symptoms),
            "answers": dict(self.answers),
            "asked": list(self.asked),
            "pending_q": self.pending_q,
            "pending_field": self.pending_field,
            "ai_extract_calls": self.ai_extract_calls,
            "media_analyses": self.media_analyses,
            "draft": dict(self.draft),
            "last_diagnosis_id": self.last_diagnosis_id,
            "safety_shown": self.safety_shown,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ConvState":
        if not data:
            return cls()
        return cls(
            state=data.get("state", "INTAKE"),
            vehicle=dict(data.get("vehicle", {})),
            vehicle_asked=bool(data.get("vehicle_asked", False)),
            symptoms=list(data.get("symptoms", [])),
            answers=dict(data.get("answers", {})),
            asked=list(data.get("asked", [])),
            pending_q=data.get("pending_q"),
            pending_field=data.get("pending_field"),
            ai_extract_calls=int(data.get("ai_extract_calls", 0)),
            media_analyses=int(data.get("media_analyses", 0)),
            draft=dict(data.get("draft", {})),
            last_diagnosis_id=data.get("last_diagnosis_id"),
            safety_shown=bool(data.get("safety_shown", False)),
        )


@dataclass
class Event:
    text: str | None = None
    choice: dict[str, str] | None = None  # {question_id, option_id}
    ai_symptoms: list[str] | None = None
    media: list[dict[str, Any]] | None = None
    booking_created: dict[str, Any] | None = None
    booking_error: dict[str, Any] | None = None  # {code, message, alternatives: list[str]}


@dataclass
class Ranked:
    cause_key: str
    score: float
    confidence: float
    why: list[str]


@dataclass
class DiagnosisData:
    top: dict[str, Any]  # {cause_key, label, description, confidence}
    ranked: list[dict[str, Any]]  # top 3 Ranked as dict
    severity: int
    safety_alert: str | None
    service: dict[str, Any]  # {key, name, description, price_min, price_max, currency: "INR", duration_hours}
    evidence_hash: str


@dataclass
class StepResult:
    state: ConvState
    messages: list[dict[str, Any]]
    replies: list[dict[str, str]]
    actions: dict[str, Any] | None = None
    diagnosis: DiagnosisData | None = None

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any
import yaml
from django.db import connection

DATA_DIR = Path(__file__).resolve().parent / 'data'


@dataclass(frozen=True)
class ServiceD:
    key: str
    name: str
    description: str
    price_min: int
    price_max: int
    duration_hours: float


@dataclass(frozen=True)
class OptionD:
    id: str
    label: str
    keywords: tuple[str, ...]
    effects: dict[str, float]


@dataclass(frozen=True)
class QuestionD:
    key: str
    text: str
    applies_when: tuple[str, ...]
    options: tuple[OptionD, ...]


@dataclass(frozen=True)
class SymptomD:
    key: str
    label: str
    category: str
    keywords: tuple[str, ...]
    red_flag: bool
    safety_msg: str


@dataclass(frozen=True)
class CauseD:
    key: str
    label: str
    description: str
    severity: int
    service_key: str
    symptoms: dict[str, float]


@dataclass(frozen=True)
class MechanicD:
    id: int | None
    name: str
    city: str
    phone: str
    active: bool


@dataclass(frozen=True)
class KB:
    services: dict[str, ServiceD]
    symptoms: dict[str, SymptomD]
    causes: dict[str, CauseD]
    questions: dict[str, QuestionD]
    mechanics: list[MechanicD]
    symptoms_by_keyword: dict[str, list[str]]
    lexicon_terms: frozenset[str]
    lexicon_makes: frozenset[str]
    lexicon_models: frozenset[str]


def _load_yaml(filename: str) -> Any:
    file_path = DATA_DIR / filename
    if not file_path.exists():
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or []


def _load_lexicon() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    lexicon_data = _load_yaml('lexicon.yaml')
    if isinstance(lexicon_data, dict):
        terms = frozenset(t.lower() for t in lexicon_data.get('terms', []))
        makes = frozenset(m.lower() for m in lexicon_data.get('makes', []))
        models = frozenset(m.lower() for m in lexicon_data.get('models', []))
        return terms, makes, models
    return frozenset(), frozenset(), frozenset()


def _load_from_yaml() -> KB:
    terms, makes, models = _load_lexicon()

    services_raw = _load_yaml('services.yaml')
    services: dict[str, ServiceD] = {}
    for s in services_raw:
        services[s['key']] = ServiceD(
            key=s['key'],
            name=s['name'],
            description=s['description'],
            price_min=int(s['price_min']),
            price_max=int(s['price_max']),
            duration_hours=float(s['duration_hours']),
        )

    symptoms_raw = _load_yaml('symptoms.yaml')
    symptoms: dict[str, SymptomD] = {}
    symptoms_by_keyword: dict[str, list[str]] = {}
    for s in symptoms_raw:
        k = s['key']
        kw_list = [str(x).lower().strip() for x in s.get('keywords', [])]
        symptoms[k] = SymptomD(
            key=k,
            label=s['label'],
            category=s.get('category', 'general'),
            keywords=tuple(kw_list),
            red_flag=bool(s.get('red_flag', False)),
            safety_msg=s.get('safety_msg', '') or '',
        )
        for kw in kw_list:
            symptoms_by_keyword.setdefault(kw, []).append(k)

    causes_raw = _load_yaml('causes.yaml')
    causes: dict[str, CauseD] = {}
    for c in causes_raw:
        symptom_weights = {
            sk: float(w) for sk, w in c.get('symptoms', {}).items()
        }
        causes[c['key']] = CauseD(
            key=c['key'],
            label=c['label'],
            description=c['description'],
            severity=int(c.get('severity', 2)),
            service_key=c['service'],
            symptoms=symptom_weights,
        )

    questions_raw = _load_yaml('questions.yaml')
    questions: dict[str, QuestionD] = {}
    for q in questions_raw:
        opts: list[OptionD] = []
        for o in q.get('options', []):
            opts.append(
                OptionD(
                    id=o['id'],
                    label=o['label'],
                    keywords=tuple(str(x).lower().strip() for x in o.get('keywords', [])),
                    effects={str(ck): float(d) for ck, d in o.get('effects', {}).items()},
                )
            )
        questions[q['key']] = QuestionD(
            key=q['key'],
            text=q['text'],
            applies_when=tuple(q.get('applies_when', [])),
            options=tuple(opts),
        )

    mechanics_raw = _load_yaml('mechanics.yaml')
    mechanics: list[MechanicD] = []
    for idx, m in enumerate(mechanics_raw, start=1):
        mechanics.append(
            MechanicD(
                id=idx,
                name=m['name'],
                city=m['city'],
                phone=m['phone'],
                active=bool(m.get('active', True)),
            )
        )

    return KB(
        services=services,
        symptoms=symptoms,
        causes=causes,
        questions=questions,
        mechanics=mechanics,
        symptoms_by_keyword=symptoms_by_keyword,
        lexicon_terms=terms,
        lexicon_makes=makes,
        lexicon_models=models,
    )


def _load_from_db() -> KB | None:
    try:
        from apps.kb.models import ServiceCatalog, Symptom, Cause, Question, Mechanic
        if not ServiceCatalog.objects.exists():
            return None

        terms, makes, models = _load_lexicon()

        services: dict[str, ServiceD] = {}
        for s in ServiceCatalog.objects.all():
            services[s.key] = ServiceD(
                key=s.key,
                name=s.name,
                description=s.description,
                price_min=s.price_min,
                price_max=s.price_max,
                duration_hours=s.duration_hours,
            )

        symptoms: dict[str, SymptomD] = {}
        symptoms_by_keyword: dict[str, list[str]] = {}
        for s in Symptom.objects.all():
            kw_list = [str(x).lower().strip() for x in s.keywords]
            symptoms[s.key] = SymptomD(
                key=s.key,
                label=s.label,
                category=s.category,
                keywords=tuple(kw_list),
                red_flag=s.red_flag,
                safety_msg=s.safety_msg or '',
            )
            for kw in kw_list:
                symptoms_by_keyword.setdefault(kw, []).append(s.key)

        causes: dict[str, CauseD] = {}
        for c in Cause.objects.select_related('service').prefetch_related('symptom_links__symptom').all():
            weights = {
                link.symptom.key: link.weight
                for link in c.symptom_links.all()
            }
            causes[c.key] = CauseD(
                key=c.key,
                label=c.label,
                description=c.description,
                severity=c.severity,
                service_key=c.service.key,
                symptoms=weights,
            )

        questions: dict[str, QuestionD] = {}
        for q in Question.objects.all():
            opts: list[OptionD] = []
            for o in q.options:
                opts.append(
                    OptionD(
                        id=o['id'],
                        label=o['label'],
                        keywords=tuple(str(x).lower().strip() for x in o.get('keywords', [])),
                        effects={str(ck): float(d) for ck, d in o.get('effects', {}).items()},
                    )
                )
            questions[q.key] = QuestionD(
                key=q.key,
                text=q.text,
                applies_when=tuple(q.applies_when),
                options=tuple(opts),
            )

        mechanics: list[MechanicD] = []
        for m in Mechanic.objects.all():
            mechanics.append(
                MechanicD(
                    id=m.id,
                    name=m.name,
                    city=m.city,
                    phone=m.phone,
                    active=m.active,
                )
            )

        return KB(
            services=services,
            symptoms=symptoms,
            causes=causes,
            questions=questions,
            mechanics=mechanics,
            symptoms_by_keyword=symptoms_by_keyword,
            lexicon_terms=terms,
            lexicon_makes=makes,
            lexicon_models=models,
        )
    except Exception:
        return None


@lru_cache(maxsize=1)
def load_kb() -> KB:
    kb = _load_from_db()
    if kb is not None:
        return kb
    return _load_from_yaml()


def clear_kb_cache() -> None:
    load_kb.cache_clear()

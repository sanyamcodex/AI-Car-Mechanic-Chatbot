from pathlib import Path
from typing import Any
import yaml
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.kb.models import ServiceCatalog, Symptom, Cause, CauseSymptom, Question, Mechanic
from apps.kb.loader import clear_kb_cache

DATA_DIR = Path(__file__).resolve().parent.parent.parent / 'data'


def _load_yaml(filename: str) -> Any:
    file_path = DATA_DIR / filename
    if not file_path.exists():
        raise CommandError(f"Required YAML data file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
        if data is None:
            raise CommandError(f"Data file is empty: {file_path}")
        return data


class Command(BaseCommand):
    help = 'Seeds knowledge base from YAML files with strict integrity checks.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Loading YAML knowledge base files...")
        services_data = _load_yaml('services.yaml')
        symptoms_data = _load_yaml('symptoms.yaml')
        causes_data = _load_yaml('causes.yaml')
        questions_data = _load_yaml('questions.yaml')
        mechanics_data = _load_yaml('mechanics.yaml')

        service_keys = {s['key'] for s in services_data}
        symptom_keys = {s['key'] for s in symptoms_data}
        cause_keys = {c['key'] for c in causes_data}

        # 1. Check cause references
        for c in causes_data:
            svc = c.get('service')
            if svc not in service_keys:
                raise CommandError(f"Cause '{c.get('key')}' references unknown service '{svc}'")
            for sym in c.get('symptoms', {}).keys():
                if sym not in symptom_keys:
                    raise CommandError(f"Cause '{c.get('key')}' references unknown symptom '{sym}'")

        # 2. Check question references and coverage
        symptom_question_counts = {k: 0 for k in symptom_keys}
        for q in questions_data:
            applies = q.get('applies_when', [])
            for sym in applies:
                if sym not in symptom_keys:
                    raise CommandError(f"Question '{q.get('key')}' references unknown symptom '{sym}' in applies_when")
                symptom_question_counts[sym] += 1

            for opt in q.get('options', []):
                for ck in opt.get('effects', {}).keys():
                    if ck not in cause_keys:
                        raise CommandError(
                            f"Question '{q.get('key')}' option '{opt.get('id')}' references unknown cause '{ck}' in effects"
                        )

        # 3. Check every symptom appears in applies_when of >= 2 questions
        for sym, count in symptom_question_counts.items():
            if count < 2:
                raise CommandError(f"Symptom '{sym}' appears in only {count} questions (minimum 2 required).")

        # 4. Seed services
        services_seeded = 0
        service_objs = {}
        for s in services_data:
            obj, _ = ServiceCatalog.objects.update_or_create(
                key=s['key'],
                defaults={
                    'name': s['name'],
                    'description': s['description'],
                    'price_min': s['price_min'],
                    'price_max': s['price_max'],
                    'duration_hours': float(s['duration_hours']),
                },
            )
            service_objs[s['key']] = obj
            services_seeded += 1

        # 5. Seed symptoms
        symptoms_seeded = 0
        symptom_objs = {}
        for s in symptoms_data:
            obj, _ = Symptom.objects.update_or_create(
                key=s['key'],
                defaults={
                    'label': s['label'],
                    'category': s.get('category', 'general'),
                    'keywords': [str(k).lower().strip() for k in s.get('keywords', [])],
                    'red_flag': bool(s.get('red_flag', False)),
                    'safety_msg': s.get('safety_msg', '') or '',
                },
            )
            symptom_objs[s['key']] = obj
            symptoms_seeded += 1

        # 6. Seed causes & links
        causes_seeded = 0
        links_seeded = 0
        for c in causes_data:
            cause_obj, _ = Cause.objects.update_or_create(
                key=c['key'],
                defaults={
                    'label': c['label'],
                    'description': c['description'],
                    'severity': int(c.get('severity', 2)),
                    'service': service_objs[c['service']],
                },
            )
            causes_seeded += 1

            for sym_key, weight in c.get('symptoms', {}).items():
                CauseSymptom.objects.update_or_create(
                    cause=cause_obj,
                    symptom=symptom_objs[sym_key],
                    defaults={'weight': float(weight)},
                )
                links_seeded += 1

        # 7. Seed questions
        questions_seeded = 0
        for q in questions_data:
            Question.objects.update_or_create(
                key=q['key'],
                defaults={
                    'text': q['text'],
                    'applies_when': q.get('applies_when', []),
                    'options': q.get('options', []),
                },
            )
            questions_seeded += 1

        # 8. Seed mechanics
        mechanics_seeded = 0
        for m in mechanics_data:
            Mechanic.objects.update_or_create(
                name=m['name'],
                city=m['city'],
                defaults={
                    'phone': m['phone'],
                    'active': bool(m.get('active', True)),
                },
            )
            mechanics_seeded += 1

        clear_kb_cache()

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding completed successfully:\n"
                f"- Services: {services_seeded}\n"
                f"- Symptoms: {symptoms_seeded}\n"
                f"- Causes: {causes_seeded}\n"
                f"- Cause-Symptom Links: {links_seeded}\n"
                f"- Questions: {questions_seeded}\n"
                f"- Mechanics: {mechanics_seeded}"
            )
        )

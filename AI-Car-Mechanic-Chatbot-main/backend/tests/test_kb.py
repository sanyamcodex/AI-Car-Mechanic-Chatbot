import pytest
from django.core.management import call_command
from apps.kb.models import ServiceCatalog, Symptom, Cause, CauseSymptom, Question, Mechanic
from apps.kb.loader import load_kb, clear_kb_cache

CANONICAL_SYMPTOMS = {
    'engine_no_crank', 'engine_cranks_no_start', 'slow_crank_click', 'engine_stalls',
    'rough_idle', 'low_power', 'poor_mileage', 'overheating', 'coolant_leak', 'oil_leak',
    'blue_smoke', 'white_smoke', 'black_smoke', 'check_engine_light', 'battery_light',
    'oil_pressure_light', 'abs_light', 'brake_squeal', 'brake_grinding', 'soft_brake_pedal',
    'steering_vibration', 'vibration_speed', 'pulling_to_side', 'steering_hard', 'clunk_bumps',
    'ac_not_cooling', 'clutch_slipping', 'hard_gear_shift', 'tire_flat', 'uneven_tire_wear',
    'burning_smell', 'fuel_smell', 'battery_drain', 'headlights_dim'
}

EXPECTED_RED_FLAGS = {
    'soft_brake_pedal', 'overheating', 'fuel_smell', 'burning_smell',
    'oil_pressure_light', 'steering_hard', 'white_smoke'
}

GOLDEN_SCENARIOS = {
    'brake_squeal': 'worn_brake_pads',
    'engine_no_crank': 'dead_battery',
    'slow_crank_click': 'weak_battery',
    'overheating': 'low_coolant',
    'ac_not_cooling': 'low_refrigerant',
    'tire_flat': 'puncture',
}


@pytest.mark.django_db
def test_seed_kb_idempotent_no_duplicates():
    # Run first time
    call_command('seed_kb')
    c_svc = ServiceCatalog.objects.count()
    c_sym = Symptom.objects.count()
    c_cau = Cause.objects.count()
    c_lnk = CauseSymptom.objects.count()
    c_q = Question.objects.count()
    c_m = Mechanic.objects.count()

    assert c_svc >= 18
    assert c_sym == 34
    assert c_cau >= 45
    assert c_q >= 50
    assert c_m == 6

    # Run second time - counts must remain identical
    call_command('seed_kb')
    assert ServiceCatalog.objects.count() == c_svc
    assert Symptom.objects.count() == c_sym
    assert Cause.objects.count() == c_cau
    assert CauseSymptom.objects.count() == c_lnk
    assert Question.objects.count() == c_q
    assert Mechanic.objects.count() == c_m


@pytest.mark.django_db
def test_kb_integrity_and_canonical_symptoms():
    call_command('seed_kb')

    symptoms = Symptom.objects.all()
    symptom_keys = {s.key for s in symptoms}
    assert symptom_keys == CANONICAL_SYMPTOMS

    red_flag_keys = {s.key for s in symptoms if s.red_flag}
    assert red_flag_keys == EXPECTED_RED_FLAGS

    for s in symptoms:
        if s.red_flag:
            assert len(s.safety_msg.strip()) > 0

    causes = Cause.objects.select_related('service').prefetch_related('symptom_links__symptom').all()
    for cause in causes:
        assert cause.service is not None
        assert cause.symptom_links.count() >= 1


@pytest.mark.django_db
def test_each_symptom_has_at_least_two_questions():
    call_command('seed_kb')
    questions = Question.objects.all()

    symptom_counts = {sym: 0 for sym in CANONICAL_SYMPTOMS}
    for q in questions:
        for sym in q.applies_when:
            assert sym in CANONICAL_SYMPTOMS
            symptom_counts[sym] += 1

    for sym, count in symptom_counts.items():
        assert count >= 2, f"Symptom '{sym}' has only {count} questions (minimum 2 required)."


@pytest.mark.django_db
def test_golden_scenarios_top_ranked_cause():
    call_command('seed_kb')
    clear_kb_cache()
    kb = load_kb()

    for sym_key, expected_cause_key in GOLDEN_SCENARIOS.items():
        # Score causes based on the single symptom weight
        candidate_scores: dict[str, float] = {}
        for cause_key, cause in kb.causes.items():
            if sym_key in cause.symptoms:
                candidate_scores[cause_key] = cause.symptoms[sym_key]

        assert len(candidate_scores) > 0, f"No causes found for symptom '{sym_key}'"

        # Sort candidate causes descending by weight
        top_cause = max(candidate_scores.items(), key=lambda x: x[1])[0]
        assert top_cause == expected_cause_key, (
            f"For symptom '{sym_key}', expected top cause '{expected_cause_key}', "
            f"but got '{top_cause}' (scores: {candidate_scores})"
        )


@pytest.mark.django_db
def test_lexicon_loader():
    clear_kb_cache()
    kb = load_kb()
    assert len(kb.lexicon_terms) >= 300
    assert len(kb.lexicon_makes) >= 40

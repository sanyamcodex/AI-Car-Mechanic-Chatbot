from backend.engine.types import ConvState
from backend.engine.scoring import rank, next_question, is_conclusive, build_diagnosis
from backend.tests.engine.fixtures import get_fixture_kb


def test_ranking_and_determinism():
    kb = get_fixture_kb()
    state = ConvState(symptoms=["brake_squeal"])

    ranked1 = rank(kb, state)
    ranked2 = rank(kb, state)

    assert len(ranked1) > 0
    assert ranked1[0].cause_key == "worn_brake_pads"
    # Determinism
    assert ranked1 == ranked2

    # Answers modify score
    state.answers["q_brake_when"] = "only_braking"
    ranked3 = rank(kb, state)
    assert ranked3[0].score > ranked1[0].score


def test_next_question_selection():
    kb = get_fixture_kb()
    state = ConvState(symptoms=["brake_squeal"])
    ranked = rank(kb, state)

    q = next_question(kb, state, ranked)
    assert q is not None
    assert q.key in ("q_brake_when", "q_brake_pedal_feel")


def test_is_conclusive_rule():
    kb = get_fixture_kb()
    state = ConvState(symptoms=["brake_squeal"])
    ranked = rank(kb, state)

    # 0 answers -> not conclusive
    assert not is_conclusive(state, ranked, kb.questions["q_brake_when"])

    # 1 answer -> not conclusive (MIN_Q = 2)
    state.answers["q_brake_when"] = "only_braking"
    assert not is_conclusive(state, ranked, kb.questions["q_brake_pedal_feel"])

    # 2 answers with high confidence and margin >= 0.15 -> conclusive
    state.answers["q_brake_pedal_feel"] = "normal_effort"
    ranked_2 = rank(kb, state)
    assert is_conclusive(state, ranked_2, None)


def test_build_diagnosis():
    kb = get_fixture_kb()
    state = ConvState(symptoms=["brake_squeal"], answers={"q_brake_when": "only_braking"})
    ranked = rank(kb, state)

    diag = build_diagnosis(kb, state, ranked)
    assert diag.top["cause_key"] == "worn_brake_pads"
    assert diag.service["key"] == "brake_service"
    assert diag.service["price_min"] == 1500
    assert len(diag.evidence_hash) == 40

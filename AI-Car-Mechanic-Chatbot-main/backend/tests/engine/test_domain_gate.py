from engine.domain_gate import gate, detect_intent
from tests.engine.fixtures import get_fixture_kb


def test_domain_gate_phrases():
    kb = get_fixture_kb()

    # 1. Car / Mechanical in-scope phrases (score >= 1)
    car_phrases = [
        "my car brake is making squeal noise",
        "engine is overheating with coolant steam",
        "the brakes are grinding when I stop",
        "car won't start and no crank",
        "is it the radiator or battery",
        "my swift has brake squeak",
        "hyundai engine overheating on highway",
        "need a mechanic for clutch and pad service",
    ]
    for phrase in car_phrases:
        res = gate(phrase, kb)
        assert res["score"] >= 1, f"Expected score >= 1 for car phrase: {phrase}"

    # 2. Off-topic phrases (score == 0)
    off_topic_phrases = [
        "what is the weather in Delhi today",
        "tell me a joke about coding",
        "how do I make a chocolate cake",
        "who won the cricket match yesterday",
        "write a python script for sorting lists",
        "can you help me with my chemistry homework",
        "book a flight to Mumbai",
        "what movies are showing tonight",
    ]
    for phrase in off_topic_phrases:
        res = gate(phrase, kb)
        assert res["score"] == 0, f"Expected score 0 for off-topic phrase: {phrase}"
        assert res["intent"] == "other"

    # 3. Greetings (intent == 'greeting')
    greetings = [
        "hi",
        "hello there",
        "hey mechanic",
        "namaste sir",
        "good morning",
        "good afternoon",
    ]
    for phrase in greetings:
        assert detect_intent(phrase) == "greeting", f"Failed greeting: {phrase}"
        res = gate(phrase, kb)
        assert res["intent"] == "greeting"

    # 4. Yes confirmations (intent == 'yes')
    yes_phrases = [
        "yes",
        "yeah sure",
        "yep",
        "okay please",
        "book it",
        "haanji please",
    ]
    for phrase in yes_phrases:
        assert detect_intent(phrase) == "yes", f"Failed yes intent: {phrase}"

    # 5. No / decline (intent == 'no')
    no_phrases = [
        "no",
        "nope",
        "not now",
        "cancel",
        "nahi",
    ]
    for phrase in no_phrases:
        assert detect_intent(phrase) == "no", f"Failed no intent: {phrase}"

    # 6. IDK / Not sure (intent == 'idk')
    idk_phrases = [
        "not sure",
        "don't know",
        "idk",
        "no idea",
    ]
    for phrase in idk_phrases:
        assert detect_intent(phrase) == "idk", f"Failed idk intent: {phrase}"

    # 7. Restart (intent == 'restart')
    restart_phrases = [
        "start over",
        "new issue",
        "another problem",
    ]
    for phrase in restart_phrases:
        assert detect_intent(phrase) == "restart", f"Failed restart intent: {phrase}"

    # Total phrases tested >= 25 (8 car + 8 off-topic + 6 greetings + 6 yes + 5 no + 4 idk + 3 restart = 40 phrases)
    total_phrases = len(car_phrases) + len(off_topic_phrases) + len(greetings) + len(yes_phrases) + len(no_phrases) + len(idk_phrases) + len(restart_phrases)
    assert total_phrases >= 25

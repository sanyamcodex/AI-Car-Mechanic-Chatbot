from apps.kb.loader import (
    KB,
    ServiceD,
    SymptomD,
    CauseD,
    QuestionD,
    OptionD,
    MechanicD,
)


def get_fixture_kb() -> KB:
    services = {
        "brake_service": ServiceD(
            key="brake_service",
            name="Brake pad & disc service",
            description="Brake inspection and replacement",
            price_min=1500,
            price_max=6000,
            duration_hours=2.0,
        ),
        "cooling_system_service": ServiceD(
            key="cooling_system_service",
            name="Cooling system flush & repair",
            description="Radiator and coolant service",
            price_min=1800,
            price_max=5500,
            duration_hours=2.0,
        ),
        "battery_service": ServiceD(
            key="battery_service",
            name="Battery replacement",
            description="Battery check and installation",
            price_min=3500,
            price_max=7500,
            duration_hours=1.0,
        ),
    }

    symptoms = {
        "brake_squeal": SymptomD(
            key="brake_squeal",
            label="Squealing when braking",
            category="brakes",
            keywords=("squeal", "squeak", "brake noise", "screech"),
            red_flag=False,
            safety_msg="",
        ),
        "brake_grinding": SymptomD(
            key="brake_grinding",
            label="Metallic grinding noise",
            category="brakes",
            keywords=("grinding", "metal on metal"),
            red_flag=False,
            safety_msg="",
        ),
        "overheating": SymptomD(
            key="overheating",
            label="Engine overheating",
            category="cooling",
            keywords=("overheating", "engine hot", "temp needle red"),
            red_flag=True,
            safety_msg="Stop the engine immediately and let it cool. Severe risk of engine seizure.",
        ),
        "engine_no_crank": SymptomD(
            key="engine_no_crank",
            label="Car won't start or crank",
            category="electrical",
            keywords=("no crank", "won't start", "dead key"),
            red_flag=False,
            safety_msg="",
        ),
    }

    symptoms_by_keyword: dict[str, list[str]] = {}
    for sym_key, sym_obj in symptoms.items():
        for kw in sym_obj.keywords:
            symptoms_by_keyword.setdefault(kw, []).append(sym_key)

    causes = {
        "worn_brake_pads": CauseD(
            key="worn_brake_pads",
            label="Worn brake pads",
            description="Brake pads worn down to wear indicators.",
            severity=2,
            service_key="brake_service",
            symptoms={"brake_squeal": 0.95, "brake_grinding": 0.50},
        ),
        "warped_rotors": CauseD(
            key="warped_rotors",
            label="Warped brake rotors",
            description="Brake discs have uneven surface runout.",
            severity=2,
            service_key="brake_service",
            symptoms={"brake_squeal": 0.30},
        ),
        "low_coolant": CauseD(
            key="low_coolant",
            label="Low engine coolant level",
            description="Coolant level dropped in radiator and reservoir.",
            severity=3,
            service_key="cooling_system_service",
            symptoms={"overheating": 0.95},
        ),
        "dead_battery": CauseD(
            key="dead_battery",
            label="Dead car battery",
            description="Battery voltage dropped below starter threshold.",
            severity=2,
            service_key="battery_service",
            symptoms={"engine_no_crank": 0.95},
        ),
    }

    questions = {
        "q_brake_when": QuestionD(
            key="q_brake_when",
            text="When do you hear the brake noise?",
            applies_when=("brake_squeal", "brake_grinding"),
            options=(
                OptionD(
                    id="only_braking",
                    label="Only when braking",
                    keywords=("braking", "pedal", "pressing"),
                    effects={"worn_brake_pads": 0.60, "warped_rotors": 0.10},
                ),
                OptionD(
                    id="all_the_time",
                    label="Constantly while rolling",
                    keywords=("always", "rolling", "all the time"),
                    effects={"worn_brake_pads": 0.20, "warped_rotors": 0.40},
                ),
            ),
        ),
        "q_brake_pedal_feel": QuestionD(
            key="q_brake_pedal_feel",
            text="How does the brake pedal feel when stopping?",
            applies_when=("brake_squeal", "brake_grinding"),
            options=(
                OptionD(
                    id="normal_effort",
                    label="Normal pedal effort",
                    keywords=("normal", "fine", "firm"),
                    effects={"worn_brake_pads": 0.50},
                ),
                OptionD(
                    id="pulsating_pedal",
                    label="Pulsating or vibrating pedal",
                    keywords=("pulsating", "vibrating", "shaking"),
                    effects={"warped_rotors": 0.80, "worn_brake_pads": -0.20},
                ),
            ),
        ),
        "q_coolant_steam": QuestionD(
            key="q_coolant_steam",
            text="Do you see steam coming from the radiator cap?",
            applies_when=("overheating",),
            options=(
                OptionD(
                    id="steam_yes",
                    label="Yes, steam from hood",
                    keywords=("yes", "steam"),
                    effects={"low_coolant": 0.70},
                ),
                OptionD(
                    id="steam_no",
                    label="No steam",
                    keywords=("no", "no steam"),
                    effects={"low_coolant": 0.30},
                ),
            ),
        ),
    }

    mechanics = [
        MechanicD(id=1, name="Rajesh Kumar", city="Meerut", phone="9812345670", active=True),
        MechanicD(id=2, name="Amit Sharma", city="Meerut", phone="9812345671", active=True),
        MechanicD(id=3, name="Suresh Verma", city="Delhi", phone="9812345672", active=True),
    ]

    lexicon_terms = frozenset([
        "car", "engine", "brake", "brakes", "pad", "rotor", "coolant", "radiator",
        "overheating", "squeal", "noise", "battery", "starter", "clutch", "mechanic",
        "service", "repair", "driving", "pedal"
    ])
    lexicon_makes = frozenset(["maruti", "hyundai", "tata", "honda", "toyota", "mahindra"])
    lexicon_models = frozenset(["swift", "i20", "nexon", "city", "creta", "baleno"])

    return KB(
        services=services,
        symptoms=symptoms,
        causes=causes,
        questions=questions,
        mechanics=mechanics,
        symptoms_by_keyword=symptoms_by_keyword,
        lexicon_terms=lexicon_terms,
        lexicon_makes=lexicon_makes,
        lexicon_models=lexicon_models,
    )

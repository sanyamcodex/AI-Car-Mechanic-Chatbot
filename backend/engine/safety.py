from apps.kb.loader import KB


def red_flags(kb: KB, symptoms: list[str]) -> list[str]:
    messages: list[str] = []
    for sym in symptoms:
        if sym in kb.symptoms:
            s_obj = kb.symptoms[sym]
            if s_obj.red_flag and s_obj.safety_msg:
                messages.append(s_obj.safety_msg)
    return messages


def format_safety_prefix(msg: str) -> str:
    return f"Safety first: {msg}\n\n"

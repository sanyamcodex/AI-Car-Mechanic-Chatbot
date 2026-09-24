from uuid import UUID


def extract_symptoms(text: str, conversation_id: UUID | None = None) -> list[str]:
    return []


def analyze_media(
    path: str,
    kind: str,
    sha256: str,
    conversation_id: UUID | None = None,
) -> dict | None:
    return None

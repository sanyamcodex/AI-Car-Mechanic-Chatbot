import hashlib
import json
import logging
import time
from uuid import UUID
from typing import Any
from django.conf import settings
from google import genai
from google.genai import types

from apps.core.models import AICache, AIUsageLog
from apps.kb.loader import load_kb

logger = logging.getLogger(__name__)


def _is_ai_enabled() -> bool:
    return bool(getattr(settings, 'AI_ENABLED', True) and getattr(settings, 'GEMINI_API_KEY', ''))


def _get_client() -> genai.Client | None:
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


def extract_symptoms(text: str, conversation_id: UUID | None = None) -> list[str]:
    if not text or not text.strip():
        return []

    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash-lite')
    norm_text = text.strip().lower()
    cache_key = hashlib.sha256(f"extract:{norm_text}".encode("utf-8")).hexdigest()

    # 1. Check Cache
    cached = AICache.objects.filter(key=cache_key).first()
    if cached and isinstance(cached.response, dict):
        AIUsageLog.objects.create(
            purpose='extract_text',
            model=model_name,
            prompt_tokens=0,
            output_tokens=0,
            latency_ms=0,
            cache_hit=True,
            success=True,
            conversation_id=conversation_id,
        )
        return cached.response.get("symptoms", [])

    # 2. Check if AI enabled
    if not _is_ai_enabled():
        return []

    client = _get_client()
    if not client:
        return []

    kb = load_kb()
    canonical_keys = list(kb.symptoms.keys())

    prompt = (
        f"You are a car mechanic assistant. Extract vehicle mechanical symptoms from the user statement.\n"
        f"Only return symptom keys from this exact allowed list:\n{json.dumps(canonical_keys)}\n\n"
        f"User statement: \"{text}\"\n\n"
        f"Return strictly valid JSON in this schema:\n"
        f'{{"symptoms": ["key1", "key2"]}}'
    )

    t0 = time.time()
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        latency_ms = int((time.time() - t0) * 1000)
        raw_text = response.text or "{}"
        parsed = json.loads(raw_text)

        symptoms = [
            k for k in parsed.get("symptoms", [])
            if k in kb.symptoms
        ]

        AICache.objects.create(
            key=cache_key,
            purpose='extract_text',
            response={"symptoms": symptoms},
        )

        p_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
        o_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

        AIUsageLog.objects.create(
            purpose='extract_text',
            model=model_name,
            prompt_tokens=p_tokens,
            output_tokens=o_tokens,
            latency_ms=latency_ms,
            cache_hit=False,
            success=True,
            conversation_id=conversation_id,
        )
        return symptoms

    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        logger.warning("AI symptom extraction failed: %s", exc)
        AIUsageLog.objects.create(
            purpose='extract_text',
            model=model_name,
            prompt_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            cache_hit=False,
            success=False,
            conversation_id=conversation_id,
        )
        return []


def analyze_media(
    path: str,
    kind: str,
    sha256: str,
    conversation_id: UUID | None = None,
) -> dict[str, Any] | None:
    purpose = f"media_{kind}"
    model_name = getattr(settings, 'GEMINI_MODEL', 'gemini-2.5-flash-lite')
    cache_key = f"media:{sha256}"

    # 1. Check Cache
    cached = AICache.objects.filter(key=cache_key).first()
    if cached and isinstance(cached.response, dict):
        AIUsageLog.objects.create(
            purpose=purpose,
            model=model_name,
            prompt_tokens=0,
            output_tokens=0,
            latency_ms=0,
            cache_hit=True,
            success=True,
            conversation_id=conversation_id,
        )
        return cached.response

    # 2. Check if AI enabled
    if not _is_ai_enabled():
        return None

    client = _get_client()
    if not client:
        return None

    kb = load_kb()
    canonical_keys = list(kb.symptoms.keys())

    prompt = (
        f"You are a senior vehicle diagnostic mechanic. Inspect this vehicle media for mechanical issues or symptoms.\n"
        f"Match observed problems to canonical symptom keys from this list:\n{json.dumps(canonical_keys)}\n\n"
        f"Return strictly valid JSON in this schema:\n"
        f'{{"observations": "concise description of visible/audible fault", "symptom_keys": ["key1"], "confidence": 0.85}}'
    )

    t0 = time.time()
    try:
        # Upload media file to Gemini File API
        uploaded_gemini_file = client.files.upload(file=path)

        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_gemini_file, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        latency_ms = int((time.time() - t0) * 1000)
        raw_text = response.text or "{}"
        parsed = json.loads(raw_text)

        valid_syms = [
            k for k in parsed.get("symptom_keys", [])
            if k in kb.symptoms
        ]
        result = {
            "observations": str(parsed.get("observations", "Vehicle inspection completed.")),
            "symptom_keys": valid_syms,
            "confidence": float(parsed.get("confidence", 0.8)),
        }

        AICache.objects.create(
            key=cache_key,
            purpose=purpose,
            response=result,
        )

        p_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
        o_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0

        AIUsageLog.objects.create(
            purpose=purpose,
            model=model_name,
            prompt_tokens=p_tokens,
            output_tokens=o_tokens,
            latency_ms=latency_ms,
            cache_hit=False,
            success=True,
            conversation_id=conversation_id,
        )
        return result

    except Exception as exc:
        latency_ms = int((time.time() - t0) * 1000)
        logger.warning("AI media analysis failed: %s", exc)
        AIUsageLog.objects.create(
            purpose=purpose,
            model=model_name,
            prompt_tokens=0,
            output_tokens=0,
            latency_ms=latency_ms,
            cache_hit=False,
            success=False,
            conversation_id=conversation_id,
        )
        return None

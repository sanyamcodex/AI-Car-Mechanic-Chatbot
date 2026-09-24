from typing import Any
from uuid import UUID
from django.db import transaction
from django.utils import timezone

from apps.chat.models import Conversation, Message
from apps.kb.loader import load_kb
from apps.core import ai_client
from apps.uploads.services import attach_uploads, analyze_uploads
from apps.diagnosis.models import Diagnosis
from apps.diagnosis.services import save_diagnosis, DiagnosisSerializer
from backend.engine.types import ConvState, Event, StepResult
from backend.engine.flow import step


def apply_event(conversation: Conversation, event: Event) -> tuple[StepResult, Diagnosis | None]:
    kb = load_kb()
    state = ConvState.from_dict(conversation.slots)
    now = timezone.now()

    result = step(kb, state, event, now)

    # If action is ai_extract, run client-side AI fallback and feed back into engine
    if result.actions and result.actions.get("type") == "ai_extract":
        query_text = result.actions.get("text", "")
        ai_syms = ai_client.extract_symptoms(query_text, conversation_id=conversation.id)
        result = step(kb, result.state, Event(ai_symptoms=ai_syms), now)

    diag_obj: Diagnosis | None = None
    if result.diagnosis:
        diag_obj = save_diagnosis(conversation, result.diagnosis)
        result.state.last_diagnosis_id = str(diag_obj.id)

    conversation.slots = result.state.to_dict()
    return result, diag_obj


def handle_turn(
    conversation_id: UUID | str | None = None,
    client_msg_id: str | None = None,
    text: str | None = None,
    choice: dict[str, str] | None = None,
    upload_ids: list[UUID | str] | None = None,
) -> dict[str, Any]:
    kb = load_kb()

    with transaction.atomic():
        # 1. Idempotency check
        if client_msg_id:
            existing_msg = Message.objects.filter(client_msg_id=client_msg_id).first()
            if existing_msg:
                conv = existing_msg.conversation
                bot_msgs = conv.messages.filter(
                    sender='bot',
                    created_at__gte=existing_msg.created_at,
                ).order_by('created_at')
                last_bot = bot_msgs.last()
                suggested = (
                    last_bot.meta.get('suggested_replies', [])
                    if last_bot and isinstance(last_bot.meta, dict)
                    else []
                )
                diag_id = conv.slots.get('last_diagnosis_id')
                diag_obj = Diagnosis.objects.filter(id=diag_id).first() if diag_id else None

                return {
                    'conversation_id': conv.id,
                    'messages': list(bot_msgs),
                    'suggested_replies': suggested,
                    'diagnosis': DiagnosisSerializer(diag_obj).data if diag_obj else None,
                    'actions': None,
                }

        # 2. Get or create conversation
        if conversation_id:
            try:
                conv = Conversation.objects.select_for_update().get(id=conversation_id)
            except Conversation.DoesNotExist:
                conv = Conversation.objects.create(id=conversation_id)
        else:
            conv = Conversation.objects.create()

        # 3. Update title rule if empty
        if not conv.title:
            if text and text.strip():
                conv.title = text.strip()[:60]
            elif choice and choice.get("question_id") == "intake":
                opt_id = choice.get("option_id", "")
                if opt_id in kb.symptoms:
                    conv.title = kb.symptoms[opt_id].label[:60]
                else:
                    conv.title = opt_id[:60]
            else:
                conv.title = "Car Diagnosis"

        # 4. Save user message
        user_text = (text or "").strip()
        if not user_text and choice:
            user_text = choice.get("label") or choice.get("option_id") or ""

        user_msg = Message.objects.create(
            conversation=conv,
            sender='user',
            text=user_text,
            kind='text',
            meta={'choice': choice} if choice else {},
            client_msg_id=client_msg_id or None,
        )

        # 5. Handle uploads
        media_results: list[dict[str, Any]] | None = None
        if upload_ids:
            attach_uploads(user_msg, [str(u) for u in upload_ids])
            media_results = analyze_uploads(conv, [str(u) for u in upload_ids])

        # 6. Apply event via engine
        event = Event(text=text, choice=choice, media=media_results)
        result, diag_obj = apply_event(conv, event)

        conv.save(update_fields=['slots', 'title', 'updated_at'])

        # 7. Persist bot messages with suggested_replies attached to the last one
        created_bot_messages: list[Message] = []
        for idx, msg_dict in enumerate(result.messages):
            meta = dict(msg_dict.get('meta', {}))
            if idx == len(result.messages) - 1:
                meta['suggested_replies'] = result.replies

            b_msg = Message.objects.create(
                conversation=conv,
                sender='bot',
                text=msg_dict.get('text', ''),
                kind=msg_dict.get('kind', 'text'),
                meta=meta,
            )
            created_bot_messages.append(b_msg)

        return {
            'conversation_id': conv.id,
            'messages': created_bot_messages,
            'suggested_replies': result.replies,
            'diagnosis': DiagnosisSerializer(diag_obj).data if diag_obj else None,
            'actions': result.actions,
        }

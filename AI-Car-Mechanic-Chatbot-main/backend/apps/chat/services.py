from typing import Any
from uuid import UUID
from django.db import transaction
from django.utils import timezone

from apps.chat.models import Conversation, Message
from apps.kb.loader import load_kb
from apps.core import ai_client
from apps.core.errors import ApiException
from apps.uploads.services import attach_uploads, analyze_uploads
from apps.diagnosis.models import Diagnosis
from engine.types import ConvState, Event, StepResult
from engine.flow import step


def persist_bot_messages(
    conversation: Conversation,
    result: StepResult,
) -> list[Message]:
    created: list[Message] = []
    ai_used = bool(result.state.ai_extract_calls or result.state.media_analyses)
    for idx, msg_dict in enumerate(result.messages):
        meta = dict(msg_dict.get('meta', {}))
        meta['ai_used'] = ai_used
        if idx == len(result.messages) - 1:
            meta['suggested_replies'] = result.replies
        b_msg = Message.objects.create(
            conversation=conversation,
            sender='bot',
            text=msg_dict.get('text', ''),
            kind=msg_dict.get('kind', 'text'),
            meta=meta,
        )
        created.append(b_msg)
    return created


def _cta_payload(state_str: str, diag_obj: Diagnosis | None) -> dict[str, str] | None:
    if state_str == 'BOOKING_OFFERED' and diag_obj:
        return {'type': 'book_mechanic', 'diagnosis_id': str(diag_obj.id)}
    return None


def apply_event(conversation: Conversation, event: Event) -> tuple[StepResult, Diagnosis | None]:
    kb = load_kb()
    state = ConvState.from_dict(conversation.slots)
    now = timezone.now()

    result = step(kb, state, event, now)

    # Intermediate results (e.g. media-failure notice) must survive the AI fallback loop
    pending_msgs: list[dict[str, Any]] = []
    loops = 0
    while result.actions and result.actions.get("type") == "ai_extract" and loops < 2:
        loops += 1
        pending_msgs.extend(result.messages)
        query_text = result.actions.get("text", "")
        ai_syms = ai_client.extract_symptoms(query_text, conversation_id=conversation.id)
        result = step(kb, result.state, Event(ai_symptoms=ai_syms), now)
    if pending_msgs:
        result.messages = [*pending_msgs, *result.messages]

    diag_obj: Diagnosis | None = None
    if result.diagnosis:
        from apps.diagnosis.services import save_diagnosis
        diag_obj = save_diagnosis(conversation, result.diagnosis)
        result.state.last_diagnosis_id = str(diag_obj.id)

    conversation.slots = result.state.to_dict()
    return result, diag_obj


def _handle_create_booking_action(
    conversation: Conversation,
    result: StepResult,
) -> tuple[StepResult, Diagnosis | None]:
    from apps.booking.services import create_booking

    draft = result.actions.get("draft", {}) if result.actions else {}
    kb = load_kb()
    now = timezone.now()
    try:
        booking = create_booking(
            customer_name=draft.get("customer_name", ""),
            phone=draft.get("phone", ""),
            city=draft.get("city", ""),
            scheduled_at=draft.get("scheduled_at", ""),
            conversation_id=conversation.id,
            skip_chat_persist=True,
            notes=draft.get("notes", "") or "",
        )
        booking_data = {
            "id": str(booking.id),
            "status": booking.status,
            "service": {"key": booking.service.key, "name": booking.service.name},
            "mechanic": {
                "id": booking.mechanic.id if booking.mechanic else None,
                "name": booking.mechanic.name if booking.mechanic else "",
                "city": booking.mechanic.city if booking.mechanic else "",
            },
            "scheduled_at": booking.scheduled_at.isoformat(),
            "customer_name": booking.customer_name,
            "phone": booking.phone,
            "city": booking.city,
        }
        step_result = step(kb, result.state, Event(booking_created=booking_data), now)
        return step_result, None
    except ApiException as exc:
        return step(
            kb,
            result.state,
            Event(booking_error={
                "code": exc.code,
                "message": exc.message,
                "alternatives": (exc.details or {}).get("alternatives", []),
            }),
            now,
        ), None


def handle_turn(
    conversation_id: UUID | str | None = None,
    client_msg_id: str | None = None,
    text: str | None = None,
    choice: dict[str, str] | None = None,
    upload_ids: list[UUID | str] | None = None,
) -> dict[str, Any]:
    with transaction.atomic():
        client_key = (client_msg_id or "").strip() or None
        if client_key:
            existing_qs = Message.objects.filter(client_msg_id=client_key)
            if conversation_id:
                existing_qs = existing_qs.filter(conversation_id=conversation_id)
            existing_msg = existing_qs.select_related('conversation').first()
            if existing_msg:
                conv = existing_msg.conversation
                turn_msgs = conv.messages.filter(created_at__gte=existing_msg.created_at, sender='bot').order_by('created_at')
                last_bot = turn_msgs.filter(sender='bot').last()
                suggested = (
                    last_bot.meta.get('suggested_replies', [])
                    if last_bot and isinstance(last_bot.meta, dict)
                    else []
                )
                diag_id = conv.slots.get('last_diagnosis_id')
                diag_obj = (
                    Diagnosis.objects.select_related('top_cause__service', 'conversation').filter(id=diag_id).first()
                    if diag_id else None
                )
                state_str = conv.slots.get('state', 'INTAKE')
                return {
                    'conversation_id': conv.id,
                    'state': state_str,
                    'messages': list(turn_msgs),
                    'suggested_replies': suggested,
                    'diagnosis': diag_obj,
                    'cta': _cta_payload(state_str, diag_obj),
                    'meta': {'ai_calls': int(conv.slots.get('ai_extract_calls', 0) or 0) + int(conv.slots.get('media_analyses', 0) or 0)},
                }

        kb = load_kb()

        if conversation_id:
            try:
                conv = Conversation.objects.select_for_update().get(id=conversation_id)
            except Conversation.DoesNotExist:
                conv = Conversation.objects.create(id=conversation_id)
        else:
            conv = Conversation.objects.create()

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

        user_text = (text or "").strip()
        if not user_text and choice:
            user_text = choice.get("label") or choice.get("option_id") or ""

        user_meta: dict[str, Any] = {'choice': choice} if choice else {}
        user_msg = Message.objects.create(
            conversation=conv,
            sender='user',
            text=user_text,
            kind='media' if upload_ids and not user_text else 'text',
            meta=user_meta,
            client_msg_id=client_key,
        )

        media_results: list[dict[str, Any]] | None = None
        if upload_ids:
            attach_uploads(user_msg, [str(u) for u in upload_ids])
            media_results = analyze_uploads(conv, [str(u) for u in upload_ids])

        event = Event(text=text, choice=choice, media=media_results)
        result, diag_obj = apply_event(conv, event)

        if result.actions and result.actions.get("type") == "create_booking":
            result, _ = _handle_create_booking_action(conv, result)
            if result.state.state == "BOOKING_CONFIRMED":
                conv.status = 'completed'
            if result.diagnosis:
                from apps.diagnosis.services import save_diagnosis
                diag_obj = save_diagnosis(conv, result.diagnosis)
                result.state.last_diagnosis_id = str(diag_obj.id)

        conv.slots = result.state.to_dict()
        conv.save(update_fields=['slots', 'title', 'updated_at', 'status'])

        created_bot_messages = persist_bot_messages(conv, result)

        state_str = result.state.state
        return {
            'conversation_id': conv.id,
            'state': state_str,
            'messages': list(created_bot_messages),
            'suggested_replies': result.replies,
            'diagnosis': diag_obj,
            'cta': _cta_payload(state_str, diag_obj),
            'meta': {'ai_calls': result.state.ai_extract_calls + result.state.media_analyses},
        }

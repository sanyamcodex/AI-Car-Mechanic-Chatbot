from typing import Any
from apps.uploads.models import Upload
from apps.core import ai_client


def attach_uploads(message: Any, upload_ids: list[str]) -> None:
    if not upload_ids:
        return

    uploads = Upload.objects.filter(id__in=upload_ids)
    attachments_meta: list[dict[str, Any]] = []

    for up in uploads:
        up.message = message
        up.save(update_fields=['message'])
        attachments_meta.append({
            'id': str(up.id),
            'original_name': up.original_name,
            'kind': up.kind,
            'size_bytes': up.size_bytes,
            'mime_type': up.mime_type,
            'file_url': up.file.url if up.file else '',
        })

    if attachments_meta:
        message.meta['attachments'] = attachments_meta
        message.save(update_fields=['meta'])


def analyze_uploads(conversation: Any, upload_ids: list[str]) -> list[dict[str, Any]]:
    if not upload_ids:
        return []

    slots = conversation.slots or {}
    state_str = slots.get('state', 'INTAKE')
    analyses_done = int(slots.get('media_analyses', 0))

    uploads = Upload.objects.filter(id__in=upload_ids).order_by('created_at')
    results: list[dict[str, Any]] = []

    for up in uploads:
        # Check policy: state must be INTAKE or CLARIFYING, and analyses_done < 3
        if state_str not in ('INTAKE', 'CLARIFYING') or analyses_done >= 3:
            up.analysis_status = 'skipped'
            up.save(update_fields=['analysis_status'])
            continue

        file_path = up.file.path if up.file else ''
        res = ai_client.analyze_media(
            path=file_path,
            kind=up.kind,
            sha256=up.sha256,
            conversation_id=conversation.id,
        )

        if res is None:
            up.analysis_status = 'failed'
            up.save(update_fields=['analysis_status'])
        else:
            up.analysis_status = 'completed'
            up.analysis_result = res
            up.save(update_fields=['analysis_status', 'analysis_result'])
            analyses_done += 1
            results.append({
                'upload_id': str(up.id),
                'observations': res.get('observations', ''),
                'symptom_keys': res.get('symptom_keys', []),
                'confidence': res.get('confidence', 0.8),
            })

    return results

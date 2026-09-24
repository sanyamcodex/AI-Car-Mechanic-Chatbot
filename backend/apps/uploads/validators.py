import io
import hashlib
from typing import Any, Tuple
from django.core.files.uploadedfile import UploadedFile
from PIL import Image
import filetype

from apps.core.errors import ApiException

IMAGE_MAX_SIZE = 5 * 1024 * 1024     # 5 MB
AUDIO_MAX_SIZE = 10 * 1024 * 1024    # 10 MB
VIDEO_MAX_SIZE = 25 * 1024 * 1024    # 25 MB

ALLOWED_IMAGE_MIMES = {
    'image/jpeg': 'image',
    'image/jpg': 'image',
    'image/png': 'image',
    'image/webp': 'image',
}

ALLOWED_AUDIO_MIMES = {
    'audio/mpeg': 'audio',
    'audio/mp3': 'audio',
    'audio/wav': 'audio',
    'audio/x-wav': 'audio',
    'audio/ogg': 'audio',
    'audio/mp4': 'audio',
    'audio/m4a': 'audio',
    'audio/x-m4a': 'audio',
    'audio/aac': 'audio',
}

ALLOWED_VIDEO_MIMES = {
    'video/mp4': 'video',
    'video/webm': 'video',
    'video/quicktime': 'video',
}


def _verify_magic_bytes(header: bytes, mime_type: str) -> bool:
    # 1. JPEG
    if mime_type in ('image/jpeg', 'image/jpg'):
        return header.startswith(b'\xff\xd8\xff')

    # 2. PNG
    if mime_type == 'image/png':
        return header.startswith(b'\x89PNG\r\n\x1a\n')

    # 3. WebP
    if mime_type == 'image/webp':
        return header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WEBP'

    # 4. WAV
    if mime_type in ('audio/wav', 'audio/x-wav'):
        return header.startswith(b'RIFF') and len(header) >= 12 and header[8:12] == b'WAVE'

    # 5. MP3
    if mime_type in ('audio/mpeg', 'audio/mp3'):
        return header.startswith(b'ID3') or (
            len(header) >= 2 and header[0] == 0xFF and (header[1] & 0xE0) == 0xE0
        )

    # 6. OGG
    if mime_type == 'audio/ogg':
        return header.startswith(b'OggS')

    # 7. WebM
    if mime_type == 'video/webm':
        return header.startswith(b'\x1a\x45\xdf\xa3')

    # 8. MP4 / M4A / MOV
    if mime_type in ('video/mp4', 'audio/mp4', 'audio/m4a', 'audio/x-m4a', 'video/quicktime'):
        if len(header) >= 8 and (header[4:8] == b'ftyp' or header.startswith(b'\x00\x00\x00')):
            return True

    # Check filetype library as secondary match
    kind = filetype.guess(header)
    if kind:
        if kind.mime == mime_type:
            return True
        if mime_type in ('audio/mpeg', 'audio/mp3') and kind.mime in ('audio/mpeg', 'audio/mp3'):
            return True
        if mime_type in ('audio/m4a', 'audio/x-m4a', 'audio/mp4') and kind.mime in ('audio/mp4', 'audio/m4a', 'video/mp4'):
            return True
        if mime_type in ('video/mp4', 'video/quicktime') and kind.mime in ('video/mp4', 'video/quicktime'):
            return True

    return False


def validate_and_process_upload(uploaded_file: UploadedFile) -> Tuple[bytes, str, str, int, str]:
    raw_content = uploaded_file.read()
    size_bytes = len(raw_content)

    if size_bytes == 0:
        raise ApiException(
            code="empty_file",
            message="Uploaded file is empty.",
            status_code=400,
        )

    header = raw_content[:64]
    detected_type = filetype.guess(header)
    content_type = (uploaded_file.content_type or "").lower().strip()

    # Determine kind & normalized mime
    kind: str | None = None
    normalized_mime = content_type

    if detected_type:
        detected_mime = detected_type.mime.lower()
        if detected_mime in ALLOWED_IMAGE_MIMES:
            kind = 'image'
            normalized_mime = detected_mime
        elif detected_mime in ALLOWED_AUDIO_MIMES:
            kind = 'audio'
            normalized_mime = detected_mime
        elif detected_mime in ALLOWED_VIDEO_MIMES:
            kind = 'video'
            normalized_mime = detected_mime

    if not kind:
        if content_type in ALLOWED_IMAGE_MIMES:
            kind = 'image'
        elif content_type in ALLOWED_AUDIO_MIMES:
            kind = 'audio'
        elif content_type in ALLOWED_VIDEO_MIMES:
            kind = 'video'

    if not kind:
        raise ApiException(
            code="unsupported_media",
            message=f"File type '{content_type or 'unknown'}' is not supported.",
            status_code=415,
        )

    # Magic bytes check
    if not _verify_magic_bytes(header, normalized_mime):
        raise ApiException(
            code="unsupported_media",
            message="File contents do not match the expected media format.",
            status_code=415,
        )

    # Size limit check
    if kind == 'image' and size_bytes > IMAGE_MAX_SIZE:
        raise ApiException(
            code="payload_too_large",
            message=f"Image size exceeds the 5MB limit ({size_bytes / (1024*1024):.1f}MB).",
            status_code=413,
        )
    elif kind == 'audio' and size_bytes > AUDIO_MAX_SIZE:
        raise ApiException(
            code="payload_too_large",
            message=f"Audio size exceeds the 10MB limit ({size_bytes / (1024*1024):.1f}MB).",
            status_code=413,
        )
    elif kind == 'video' and size_bytes > VIDEO_MAX_SIZE:
        raise ApiException(
            code="payload_too_large",
            message=f"Video size exceeds the 25MB limit ({size_bytes / (1024*1024):.1f}MB).",
            status_code=413,
        )

    final_content = raw_content

    # Downscale image if width or height > 1600px
    if kind == 'image':
        try:
            image = Image.open(io.BytesIO(raw_content))
            w, h = image.size
            if w > 1600 or h > 1600:
                image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                out_buffer = io.BytesIO()
                # Maintain RGB format for JPEG
                if image.mode in ('RGBA', 'P') and normalized_mime in ('image/jpeg', 'image/jpg'):
                    image = image.convert('RGB')
                save_format = 'PNG' if normalized_mime == 'image/png' else ('WEBP' if normalized_mime == 'image/webp' else 'JPEG')
                image.save(out_buffer, format=save_format, quality=85, optimize=True)
                final_content = out_buffer.getvalue()
                size_bytes = len(final_content)
        except Exception:
            pass

    sha256 = hashlib.sha256(final_content).hexdigest()
    return final_content, normalized_mime, kind, size_bytes, sha256

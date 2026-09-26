import io
from unittest.mock import patch, MagicMock
import pytest
from PIL import Image
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.uploads.models import Upload
from apps.core.models import AICache, AIUsageLog
from apps.kb.management.commands.seed_kb import Command as SeedCommand


def _make_dummy_image(width=100, height=100, fmt="JPEG", size_bytes=None) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(255, 0, 0))
    img.save(buf, format=fmt)
    data = buf.getvalue()
    if size_bytes and len(data) < size_bytes:
        data = data + b"\x00" * (size_bytes - len(data))
    return data


def _make_dummy_wav() -> bytes:
    # 44-byte standard RIFF WAVE header
    header = (
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )
    return header


@pytest.fixture(autouse=True)
def seed_database(db):
    SeedCommand().handle()


@pytest.mark.django_db
def test_upload_success_201():
    client = APIClient()
    url = reverse('uploads')

    img_data = _make_dummy_image()
    uploaded = SimpleUploadedFile("car_engine.jpg", img_data, content_type="image/jpeg")

    res = client.post(url, {"file": uploaded}, format='multipart')
    assert res.status_code == 201
    data = res.json()
    assert data["kind"] == "image"
    assert data["mime_type"] == "image/jpeg"
    assert "id" in data
    assert Upload.objects.filter(id=data["id"]).exists()


@pytest.mark.django_db
def test_upload_payload_too_large_413():
    client = APIClient()
    url = reverse('uploads')

    # 6 MB JPEG (exceeds 5 MB limit)
    large_data = _make_dummy_image(size_bytes=6 * 1024 * 1024)
    uploaded = SimpleUploadedFile("huge.jpg", large_data, content_type="image/jpeg")

    res = client.post(url, {"file": uploaded}, format='multipart')
    assert res.status_code == 413
    data = res.json()
    assert data["error"]["code"] == "payload_too_large"


@pytest.mark.django_db
def test_upload_unsupported_media_415():
    client = APIClient()
    url = reverse('uploads')

    # Text content disguised as image/jpeg
    fake_data = b"This is not a real JPEG image at all."
    uploaded = SimpleUploadedFile("fake.jpg", fake_data, content_type="image/jpeg")

    res = client.post(url, {"file": uploaded}, format='multipart')
    assert res.status_code == 415
    data = res.json()
    assert data["error"]["code"] == "unsupported_media"


@pytest.mark.django_db
def test_analyze_with_mocked_gemini_and_cache_hit():
    client = APIClient()
    upload_url = reverse('uploads')
    chat_url = reverse('chat')

    img_data = _make_dummy_image()
    uploaded = SimpleUploadedFile("brake_disc.jpg", img_data, content_type="image/jpeg")
    u_res = client.post(upload_url, {"file": uploaded}, format='multipart')
    upload_id = u_res.json()["id"]

    mock_analysis_result = {
        "observations": "Deep grooving visible on front brake rotor and worn pads",
        "symptom_keys": ["brake_squeal"],
        "confidence": 0.90,
    }

    # 1. First chat turn with upload
    with patch('apps.core.ai_client._get_client') as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = '{"observations": "Deep grooving visible on rotor", "symptom_keys": ["brake_squeal"], "confidence": 0.9}'
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 30
        mock_client.models.generate_content.return_value = mock_response

        with override_settings(AI_ENABLED=True, GEMINI_API_KEY="test-fake-key"):
            res1 = client.post(chat_url, {
                "text": "please look at this image",
                "upload_ids": [upload_id],
                "client_msg_id": "upload-turn-1",
            }, format='json')

            assert res1.status_code == 200
            d1 = res1.json()
            conv_id = d1["conversation_id"]

            # Media analysis observation text is present
            assert any("rotor" in m["text"] for m in d1["messages"])
            assert mock_client.models.generate_content.call_count == 1

            # AICache was created
            upload_obj = Upload.objects.get(id=upload_id)
            assert AICache.objects.filter(key=f"media:{upload_obj.sha256}").exists()

            # 2. Second turn with same upload / sha256 -> must hit cache (0 Gemini calls)
            mock_client.models.generate_content.reset_mock()
            res2 = client.post(chat_url, {
                "conversation_id": conv_id,
                "text": "checking again",
                "upload_ids": [upload_id],
                "client_msg_id": "upload-turn-2",
            }, format='json')

            assert res2.status_code == 200
            assert mock_client.models.generate_content.call_count == 0

            # Cache hit was logged
            cache_hit_logs = AIUsageLog.objects.filter(cache_hit=True)
            assert cache_hit_logs.exists()


@pytest.mark.django_db
def test_disabled_ai_fallback_message():
    client = APIClient()
    upload_url = reverse('uploads')
    chat_url = reverse('chat')

    img_data = _make_dummy_image()
    uploaded = SimpleUploadedFile("sample.jpg", img_data, content_type="image/jpeg")
    u_res = client.post(upload_url, {"file": uploaded}, format='multipart')
    upload_id = u_res.json()["id"]

    with override_settings(AI_ENABLED=False, GEMINI_API_KEY=""):
        res = client.post(chat_url, {
            "text": "here is my car audio",
            "upload_ids": [upload_id],
            "client_msg_id": "disabled-ai-1",
        }, format='json')

        assert res.status_code == 200
        data = res.json()
        # Bot should emit the fallback message for disabled AI
        assert any(
            "couldn't process the media file" in m["text"].lower()
            for m in data["messages"]
        )


@pytest.mark.django_db
def test_media_analysis_cap_of_three():
    client = APIClient()
    upload_url = reverse('uploads')
    chat_url = reverse('chat')

    # Create 4 distinct uploads
    upload_ids = []
    for i in range(4):
        # vary dimensions slightly to produce distinct sha256
        img_data = _make_dummy_image(width=100 + i, height=100 + i)
        f = SimpleUploadedFile(f"photo_{i}.jpg", img_data, content_type="image/jpeg")
        r = client.post(upload_url, {"file": f}, format='multipart')
        upload_ids.append(r.json()["id"])

    with patch('apps.core.ai_client.analyze_media') as mock_ai:
        mock_ai.return_value = {
            "observations": "Visible component wear",
            "symptom_keys": ["brake_squeal"],
            "confidence": 0.85,
        }

        # Send all 4 uploads in one turn
        res = client.post(chat_url, {
            "text": "here are 4 photos of the problem",
            "upload_ids": upload_ids,
            "client_msg_id": "cap-test-1",
        }, format='json')

        assert res.status_code == 200

        # Exactly 3 were analyzed
        assert mock_ai.call_count == 3

        # First 3 uploads completed, 4th skipped
        statuses = [Upload.objects.get(id=u_id).analysis_status for u_id in upload_ids]
        assert statuses.count('completed') == 3
        assert statuses.count('skipped') == 1

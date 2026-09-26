import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.chat.models import Conversation
from apps.kb.management.commands.seed_kb import Command as SeedCommand


@pytest.fixture(autouse=True)
def seed_database(db):
    SeedCommand().handle()


@pytest.mark.django_db
def test_diagnosis_409_needs_more_info_and_force():
    client = APIClient()
    chat_url = reverse('chat')
    diag_url = reverse('diagnosis')

    # Start conversation with a symptom
    res1 = client.post(chat_url, {
        "choice": {"question_id": "intake", "option_id": "brake_squeal"},
        "client_msg_id": "d-msg-1",
    }, format='json')
    conv_id = res1.json()["conversation_id"]

    # 1. Attempt diagnosis before answering questions -> 409
    res_diag_409 = client.post(diag_url, {
        "conversation_id": conv_id,
        "force": False,
    }, format='json')

    assert res_diag_409.status_code == 409
    data_409 = res_diag_409.json()
    assert "error" in data_409
    err = data_409["error"]
    assert err["code"] == "needs_more_info"
    assert "next_question" in err["details"]
    assert "ranked" in err["details"]

    # 2. Attempt diagnosis with force=True -> 200 OK
    res_diag_forced = client.post(diag_url, {
        "conversation_id": conv_id,
        "force": True,
    }, format='json')

    assert res_diag_forced.status_code == 200
    diag_data = res_diag_forced.json()
    assert diag_data["top_cause_key"] == "worn_brake_pads"
    assert "service" in diag_data
    assert diag_data["service"]["key"] == "brake_service"

    diag_id = diag_data["id"]

    # 3. GET /api/diagnosis/<id>/
    detail_url = reverse('diagnosis-detail', kwargs={'pk': diag_id})
    res_detail = client.get(detail_url)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["id"] == diag_id
    assert detail_data["top_cause_key"] == "worn_brake_pads"


@pytest.mark.django_db
def test_diagnosis_deduplication_by_evidence_hash():
    client = APIClient()
    chat_url = reverse('chat')
    diag_url = reverse('diagnosis')

    res1 = client.post(chat_url, {
        "choice": {"question_id": "intake", "option_id": "overheating"},
        "client_msg_id": "d-dedupe-1",
    }, format='json')
    conv_id = res1.json()["conversation_id"]

    # Generate diagnosis with force=True
    d1 = client.post(diag_url, {"conversation_id": conv_id, "force": True}, format='json').json()
    # Repeat diagnosis with force=True
    d2 = client.post(diag_url, {"conversation_id": conv_id, "force": True}, format='json').json()

    # Exact same diagnosis ID returned due to evidence_hash deduplication
    assert d1["id"] == d2["id"]
    assert d1["evidence_hash"] == d2["evidence_hash"]

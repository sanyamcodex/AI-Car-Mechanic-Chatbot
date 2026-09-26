from unittest.mock import patch
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.chat.models import Conversation, Message
from apps.kb.management.commands.seed_kb import Command as SeedCommand


@pytest.fixture(autouse=True)
def seed_database(db):
    SeedCommand().handle()


@pytest.mark.django_db
def test_off_topic_message():
    client = APIClient()
    url = reverse('chat')

    res = client.post(url, {
        "text": "what is the recipe for lasagna",
        "client_msg_id": "test-off-topic-1",
    }, format='json')

    assert res.status_code == 200
    data = res.json()
    assert len(data["messages"]) > 0
    bot_msg = data["messages"][0]
    assert "car mechanic assistant" in bot_msg["text"]
    assert len(data["suggested_replies"]) >= 4
    assert data["suggested_replies"][0]["question_id"] == "intake"


@pytest.mark.django_db
def test_follow_ups_before_diagnosis_and_zero_ai_calls():
    client = APIClient()
    url = reverse('chat')

    with patch('apps.core.ai_client.extract_symptoms') as mock_ai:
        mock_ai.return_value = []

        # Turn 1: Intake symptom
        res1 = client.post(url, {
            "choice": {"question_id": "intake", "option_id": "brake_squeal"},
            "client_msg_id": "msg-1",
        }, format='json')
        assert res1.status_code == 200
        d1 = res1.json()
        conv_id = d1["conversation_id"]
        assert d1["diagnosis"] is None
        # Vehicle question prompted
        assert d1["suggested_replies"][0]["id"] == "skip"

        # Turn 2: Skip vehicle question
        res2 = client.post(url, {
            "conversation_id": conv_id,
            "choice": {"question_id": "vehicle", "option_id": "skip"},
            "client_msg_id": "msg-2",
        }, format='json')
        assert res2.status_code == 200
        d2 = res2.json()
        assert d2["diagnosis"] is None
        assert len(d2["suggested_replies"]) >= 2
        q1_key = d2["suggested_replies"][0]["question_id"]
        q1_opt = d2["suggested_replies"][0]["id"]

        # Turn 3: Answer Q1
        res3 = client.post(url, {
            "conversation_id": conv_id,
            "choice": {"question_id": q1_key, "option_id": q1_opt},
            "client_msg_id": "msg-3",
        }, format='json')
        assert res3.status_code == 200
        d3 = res3.json()
        q2_key = d3["suggested_replies"][0]["question_id"]
        q2_opt = d3["suggested_replies"][0]["id"]

        # Turn 4: Answer Q2 -> reaches conclusive diagnosis
        res4 = client.post(url, {
            "conversation_id": conv_id,
            "choice": {"question_id": q2_key, "option_id": q2_opt},
            "client_msg_id": "msg-4",
        }, format='json')
        assert res4.status_code == 200
        d4 = res4.json()

        # Diagnosis reached!
        assert d4["diagnosis"] is not None
        assert d4["diagnosis"]["top_cause_key"] == "worn_brake_pads"
        assert d4["suggested_replies"][0]["question_id"] == "book_offer"

        # 0 AI calls made on the deterministic happy path!
        assert mock_ai.call_count == 0


@pytest.mark.django_db
def test_idempotency():
    client = APIClient()
    url = reverse('chat')

    payload = {
        "text": "my brakes are squealing",
        "client_msg_id": "idempotent-msg-1234",
    }

    res1 = client.post(url, payload, format='json')
    assert res1.status_code == 200
    d1 = res1.json()

    # Repeat with same client_msg_id
    res2 = client.post(url, payload, format='json')
    assert res2.status_code == 200
    d2 = res2.json()

    assert d1["conversation_id"] == d2["conversation_id"]
    assert len(d1["messages"]) == len(d2["messages"])
    assert d1["messages"][0]["text"] == d2["messages"][0]["text"]

    # Check total user messages in DB with this client_msg_id is exactly 1
    assert Message.objects.filter(client_msg_id="idempotent-msg-1234").count() == 1


@pytest.mark.django_db
def test_conversation_history_endpoints():
    client = APIClient()
    chat_url = reverse('chat')

    res = client.post(chat_url, {
        "text": "brake squeal",
        "client_msg_id": "hist-1",
    }, format='json')
    conv_id = res.json()["conversation_id"]

    # List conversations
    list_url = reverse('conversation-list')
    res_list = client.get(list_url)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert any(c["id"] == conv_id for c in list_data)

    # Filter with ?ids=
    res_filtered = client.get(f"{list_url}?ids={conv_id}")
    assert res_filtered.status_code == 200
    assert len(res_filtered.json()) == 1

    # Detail conversation
    detail_url = reverse('conversation-detail', kwargs={'pk': conv_id})
    res_detail = client.get(detail_url)
    assert res_detail.status_code == 200
    d_data = res_detail.json()
    assert d_data["id"] == conv_id
    assert len(d_data["messages"]) >= 2  # user + bot
    assert len(d_data["suggested_replies"]) > 0


@pytest.mark.django_db
def test_ai_fallback_triggered_on_ambiguous_text():
    client = APIClient()
    url = reverse('chat')

    with patch('apps.core.ai_client.extract_symptoms') as mock_ai:
        # User enters car word with no canonical symptom keywords matched
        mock_ai.return_value = ["engine_no_crank"]

        res = client.post(url, {
            "text": "my automobile vehicle is totally failing to work today",
            "client_msg_id": "ai-test-1",
        }, format='json')

        assert res.status_code == 200
        # AI fallback was called
        assert mock_ai.call_count == 1
        d = res.json()
        assert len(d["messages"]) > 0

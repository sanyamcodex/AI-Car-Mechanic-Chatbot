import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from apps.chat.models import Conversation, Message
from apps.core.models import AIUsageLog
from apps.kb.management.commands.seed_kb import Command as SeedCommand


@pytest.fixture(autouse=True)
def seed_database(db):
    SeedCommand().handle()


@pytest.mark.django_db
def test_stats_metrics_and_ratio_math():
    client = APIClient()
    url = reverse('stats')

    # Initial stats
    res1 = client.get(url)
    assert res1.status_code == 200
    d1 = res1.json()
    assert "conversations" in d1
    assert "messages_total" in d1
    assert "bot_messages_total" in d1
    assert "ai_calls_total" in d1
    assert "ai_call_ratio" in d1
    assert "by_purpose" in d1

    # Create dummy conversation with bot messages
    conv = Conversation.objects.create(title="Stats Test")
    Message.objects.create(conversation=conv, sender="user", text="hello")
    Message.objects.create(conversation=conv, sender="bot", text="hi there")
    Message.objects.create(conversation=conv, sender="bot", text="what issue?")

    # Create 3 AI logs
    AIUsageLog.objects.create(purpose="extract_text", model="gemini-2.5-flash-lite", latency_ms=120, success=True)
    AIUsageLog.objects.create(purpose="media_image", model="gemini-2.5-flash-lite", latency_ms=300, success=True, cache_hit=True)
    AIUsageLog.objects.create(purpose="extract_text", model="gemini-2.5-flash-lite", latency_ms=250, success=False)

    res2 = client.get(url)
    assert res2.status_code == 200
    d2 = res2.json()

    assert d2["conversations"] >= 1
    assert d2["bot_messages_total"] >= 2
    assert d2["ai_calls_total"] >= 3
    assert d2["ai_cache_hits"] >= 1
    assert d2["ai_failures"] >= 1
    assert d2["by_purpose"]["extract_text"] >= 2
    assert d2["by_purpose"]["media_image"] >= 1

    # Verify ratio math
    expected_ratio = round(d2["ai_calls_total"] / max(1, d2["bot_messages_total"]), 4)
    assert d2["ai_call_ratio"] == expected_ratio

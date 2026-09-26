import uuid
from django.db import models


class AIUsageLog(models.Model):
    PURPOSE_CHOICES = (
        ('media_image', 'Media Image'),
        ('media_audio', 'Media Audio'),
        ('media_video', 'Media Video'),
        ('extract_text', 'Extract Text'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)
    model = models.CharField(max_length=64)
    prompt_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    latency_ms = models.IntegerField(default=0)
    cache_hit = models.BooleanField(default=False)
    success = models.BooleanField(default=True)
    conversation_id = models.UUIDField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.purpose} ({self.model}) - {self.created_at}"


class AICache(models.Model):
    key = models.CharField(max_length=96, primary_key=True)
    purpose = models.CharField(max_length=32)
    response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.purpose} cache ({self.key[:8]}...)"

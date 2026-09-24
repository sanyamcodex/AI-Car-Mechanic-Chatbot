import uuid
from django.db import models


class Diagnosis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        'chat.Conversation',
        on_delete=models.CASCADE,
        related_name='diagnoses',
    )
    top_cause = models.ForeignKey(
        'kb.Cause',
        on_delete=models.PROTECT,
        related_name='diagnoses',
    )
    confidence = models.FloatField()
    severity = models.PositiveSmallIntegerField(default=2)
    ranked = models.JSONField(default=list)
    evidence_hash = models.CharField(max_length=64, db_index=True)
    safety_alert = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"Diagnosis {self.id} for {self.conversation_id} ({self.top_cause.key})"

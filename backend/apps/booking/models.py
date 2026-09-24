import uuid
from django.db import models


class Booking(models.Model):
    STATUS_CHOICES = (
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        'chat.Conversation',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookings',
    )
    diagnosis = models.ForeignKey(
        'diagnosis.Diagnosis',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='bookings',
    )
    customer_name = models.CharField(max_length=60)
    phone = models.CharField(max_length=15)
    city = models.CharField(max_length=64, db_index=True)
    service = models.ForeignKey(
        'kb.ServiceCatalog',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    mechanic = models.ForeignKey(
        'kb.Mechanic',
        on_delete=models.PROTECT,
        related_name='bookings',
    )
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    idempotency_key = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']
        constraints = [
            models.UniqueConstraint(
                fields=['mechanic', 'scheduled_at'],
                name='unique_mechanic_slot',
            )
        ]

    def __str__(self) -> str:
        return f"Booking {self.id} for {self.customer_name} ({self.scheduled_at})"

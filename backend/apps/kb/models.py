from django.db import models


class ServiceCatalog(models.Model):
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    price_min = models.IntegerField(help_text="Minimum price in INR")
    price_max = models.IntegerField(help_text="Maximum price in INR")
    duration_hours = models.FloatField(help_text="Estimated service duration in hours")

    class Meta:
        ordering = ['key']

    def __str__(self) -> str:
        return f"{self.name} (₹{self.price_min}-₹{self.price_max})"


class Symptom(models.Model):
    key = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=120)
    category = models.CharField(max_length=64)
    keywords = models.JSONField(default=list, help_text="List of keywords/phrases")
    red_flag = models.BooleanField(default=False)
    safety_msg = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ['key']

    def __str__(self) -> str:
        return self.label


class Cause(models.Model):
    SEVERITY_CHOICES = (
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Critical'),
    )

    key = models.CharField(max_length=64, unique=True, db_index=True)
    label = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    severity = models.PositiveSmallIntegerField(choices=SEVERITY_CHOICES, default=2)
    service = models.ForeignKey(ServiceCatalog, on_delete=models.CASCADE, related_name='causes')

    class Meta:
        ordering = ['key']

    def __str__(self) -> str:
        return self.label


class CauseSymptom(models.Model):
    cause = models.ForeignKey(Cause, on_delete=models.CASCADE, related_name='symptom_links')
    symptom = models.ForeignKey(Symptom, on_delete=models.CASCADE, related_name='cause_links')
    weight = models.FloatField(help_text="Weight from 0.0 to 1.0")

    class Meta:
        unique_together = ('cause', 'symptom')
        ordering = ['cause', '-weight']

    def __str__(self) -> str:
        return f"{self.cause.key} -> {self.symptom.key} ({self.weight})"


class Question(models.Model):
    key = models.CharField(max_length=64, unique=True, db_index=True)
    text = models.CharField(max_length=255)
    applies_when = models.JSONField(default=list, help_text="List of symptom keys")
    options = models.JSONField(
        default=list,
        help_text="List of dicts: [{id, label, keywords: list[str], effects: {cause_key: delta}}]"
    )

    class Meta:
        ordering = ['key']

    def __str__(self) -> str:
        return self.key


class Mechanic(models.Model):
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=64, db_index=True)
    phone = models.CharField(max_length=20)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['city', 'name']

    def __str__(self) -> str:
        return f"{self.name} ({self.city})"

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from sales.models import Customer


class Opportunity(models.Model):
    class Stage(models.TextChoices):
        NEW = 'new', 'İlk temas'
        IN_DISCUSSION = 'in_discussion', 'Görüşülüyor'
        PROPOSAL_SENT = 'proposal_sent', 'Teklif verildi'
        WON = 'won', 'Kazanıldı'
        LOST = 'lost', 'Kaybedildi'

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name='opportunities'
    )
    title = models.CharField(max_length=255)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    estimated_value = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
        null=True, blank=True,
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.title} - {self.customer} ({self.get_stage_display()})'
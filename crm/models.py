from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from sales.models import Customer


class Opportunity(models.Model):
    class Stage(models.TextChoices):
        NEW = 'new', _('İlk temas')
        IN_DISCUSSION = 'in_discussion', _('İhtiyaç analizi')
        PROPOSAL_SENT = 'proposal_sent', _('Teklif sunuldu')
        NEGOTIATION = 'negotiation', _('Pazarlık')
        WON = 'won', _('Kazanıldı')
        LOST = 'lost', _('Kaybedildi')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Aktif')
        PASSIVE = 'passive', _('Pasif')
        WON = 'won', _('Kazanıldı')
        LOST = 'lost', _('Kaybedildi')

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='opportunities'
    )
    title = models.CharField(max_length=255)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.NEW)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
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

    @property
    def is_open(self):
        return self.status in (self.Status.ACTIVE, self.Status.PASSIVE)

    def __str__(self):
        return f'{self.title} - {self.customer} ({self.get_status_display()})'

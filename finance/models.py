from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from sales.models import Order


class Invoice(models.Model):
    class Status(models.TextChoices):
        UNPAID = 'unpaid', _('Ödenmedi')
        PARTIALLY_PAID = 'partially_paid', _('Kısmen Ödendi')
        PAID = 'paid', _('Ödendi')

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='invoice')
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNPAID)

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.order.items.all()), Decimal('0'))

    @property
    def total_paid(self):
        return sum((p.amount for p in self.payments.all()), Decimal('0'))

    @property
    def balance_due(self):
        return self.total_amount - self.total_paid

    @property
    def invoice_number(self):
        year = self.issued_at.year if self.issued_at else ''
        return f'INV-{year}-{self.pk:05d}'

    def __str__(self):
        return f'{self.invoice_number} - {self.order.customer.name}'


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = 'cash', _('Nakit')
        BANK_TRANSFER = 'bank_transfer', _('Havale/EFT')
        CREDIT_CARD = 'credit_card', _('Kredi Kartı')

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    method = models.CharField(max_length=20, choices=Method.choices)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.invoice} - ₺{self.amount}'

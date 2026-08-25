from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import Business, Lot, Product


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SENT = 'sent', 'Sent to supplier'
        CONFIRMED = 'confirmed', 'Confirmed by supplier'
        PARTIALLY_RECEIVED = 'partially_received', 'Partially received'
        RECEIVED = 'received', 'Fully received'
        CANCELLED = 'cancelled', 'Cancelled'

    supplier = models.ForeignKey(
        Business, on_delete=models.PROTECT, related_name='purchase_orders'
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.DRAFT
    )
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'PO #{self.pk} - {self.supplier}'


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='purchase_order_items'
    )
    quantity_ordered = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product} x {self.quantity_ordered}'

    @property
    def quantity_received(self):
        from django.db.models import Sum
        total = self.goods_receipts.aggregate(total=Sum('quantity_received'))['total']
        return total or Decimal('0')

    @property
    def quantity_remaining(self):
        return self.quantity_ordered - self.quantity_received


class GoodsReceipt(models.Model):
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem, on_delete=models.PROTECT, related_name='goods_receipts'
    )
    lot = models.OneToOneField(
        Lot, on_delete=models.PROTECT, related_name='goods_receipt'
    )
    quantity_received = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    received_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.purchase_order_item} - {self.quantity_received} received'
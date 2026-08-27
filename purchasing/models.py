from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import Business, Lot, Product


class PurchaseOrder(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Taslak'
        SENT = 'sent', 'Tedarikçiye gönderildi'
        CONFIRMED = 'confirmed', 'Tedarikçi teyit etti'
        PARTIALLY_RECEIVED = 'partially_received', 'Kısmi teslim alındı'
        RECEIVED = 'received', 'Tam teslim alındı'
        CANCELLED = 'cancelled', 'İptal edildi'

    supplier = models.ForeignKey(
        Business, on_delete=models.PROTECT, related_name='purchase_orders'
    )
    status = models.CharField(
        max_length=25, choices=Status.choices, default=Status.DRAFT
    )
    expected_delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_editable(self):
        return self.status == self.Status.DRAFT

    @property
    def is_receivable(self):
        return self.status in (
            self.Status.SENT,
            self.Status.CONFIRMED,
            self.Status.PARTIALLY_RECEIVED,
        )

    @property
    def total_amount(self):
        return sum((item.line_total for item in self.items.all()), Decimal('0'))

    def clean(self):
        super().clean()
        if (
            self.supplier_id
            and self.supplier.business_type != Business.BusinessType.SUPPLIER
        ):
            raise ValidationError({'supplier': 'Sipariş yalnızca gerçek bir tedarikçiye açılabilir.'})

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
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )

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

    @property
    def line_total(self):
        return self.quantity_ordered * self.unit_price

    def clean(self):
        super().clean()
        if (
            self.purchase_order_id
            and self.product_id
            and self.product.business_id != self.purchase_order.supplier_id
        ):
            raise ValidationError({
                'product': 'Bu ürün seçili tedarikçinin ürün kataloğunda değil.'
            })


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

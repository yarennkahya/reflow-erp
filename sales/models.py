from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from inventory.models import Lot, Product


class Customer(models.Model):
    class CustomerType(models.TextChoices):
        WHOLESALE = 'wholesale', 'Toptan (kafe)'
        RETAIL = 'retail', 'Perakende (bireysel)'

    name = models.CharField(max_length=255)
    customer_type = models.CharField(max_length=20, choices=CustomerType.choices)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        FULFILLED = 'fulfilled', 'Fulfilled'
        CANCELLED = 'cancelled', 'Cancelled'

    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, related_name='orders'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Order #{self.pk} - {self.customer}'


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items'
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name='order_items'
    )
    lot = models.ForeignKey(
        Lot, on_delete=models.PROTECT, related_name='order_items'
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def line_total(self):
        return self.quantity * self.unit_price
        
    def __str__(self):
        return f'{self.product} x {self.quantity}'


class ReturnRequest(models.Model):
    class Reason(models.TextChoices):
        CUSTOMER_CHANGED_MIND = 'customer_changed_mind', 'Müşteri vazgeçti'
        DEFECTIVE = 'defective', 'Kusurlu ürün'

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Talep Edildi'
        COMPLETED = 'completed', 'Tamamlandı'
        REJECTED = 'rejected', 'Reddedildi'

    order_item = models.ForeignKey(
        OrderItem, on_delete=models.PROTECT, related_name='return_requests'
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    reason = models.CharField(max_length=30, choices=Reason.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.REQUESTED,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f'{self.order_item} - {self.get_reason_display()} '
            f'({self.get_status_display()})'
        )

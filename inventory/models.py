from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
class Business(models.Model):
    class BusinessType(models.TextChoices):
        SUPPLIER = 'supplier', _('Tedarikçi')
        WHOLESALE_CUSTOMER = 'wholesale_customer', _('Toptan müşteri (kafe)')
        INTERNAL = 'internal', _('İç işletme')

    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=30, choices=BusinessType.choices)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'businesses'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    class Unit(models.TextChoices):
        PIECE = 'piece', _('Adet')
        KILOGRAM = 'kg', _('Kg')
        LITER = 'liter', _('Litre')

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    unit = models.CharField(max_length=10, choices=Unit.choices)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name='products',
    )
    reorder_point = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True,
        help_text='Toplam stok bu miktarın altına düşünce otomatik taslak sipariş oluşturulur.',
    )
    reorder_quantity = models.DecimalField(
        max_digits=12, decimal_places=3, null=True, blank=True,
        help_text='Otomatik oluşturulacak taslak siparişin miktarı.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Lot(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='lots',
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name='lots',
        null=True, blank=True,
    )
    lot_code = models.CharField(max_length=100)
    expiry_date = models.DateField(db_index=True)
    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    unit_cost = models.DecimalField(
    max_digits=10, decimal_places=2, null=True, blank=True,
    help_text='Bu lotun birim başına maliyeti (opsiyonel).',
    )
    received_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date', 'received_at', 'pk']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'lot_code'],
                name='inventory_unique_product_lot_code',
            )
        ]

    @property
    def remaining_quantity(self):
        from django.db.models import Sum
        moved = self.stock_movements.aggregate(total=Sum('quantity'))['total'] or 0
        return self.quantity_received + moved

    def __str__(self):
        return f'{self.product} ({self.lot_code})'


# NOT: Bilerek MODUL seviyesinde (nested class scoping sorununu hatirla).
class MovementType(models.TextChoices):
    IN = 'IN', _('Stok girişi')
    OUT_PRODUCTION = 'OUT_PRODUCTION', _('Üretimde kullanıldı')
    OUT_SALE = 'OUT_SALE', _('Satış sevkiyatı')
    WASTE = 'WASTE', _('İmha / zayi')


class StockMovement(models.Model):
    # Geriye donuk uyumluluk: StockMovement.MovementType hala calisir.
    MovementType = MovementType

    lot = models.ForeignKey(
        Lot,
        on_delete=models.PROTECT,
        related_name='stock_movements',
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'pk']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(movement_type=MovementType.IN, quantity__gt=0)
                    | models.Q(
                        movement_type__in=[
                            MovementType.OUT_PRODUCTION,
                            MovementType.OUT_SALE,
                            MovementType.WASTE,
                        ],
                        quantity__lt=0,
                    )
                ),
                name='inventory_stock_movement_quantity_sign',
            )
        ]

    def clean(self):
        super().clean()
        if self.quantity is None:
            return

        if self.movement_type == self.MovementType.IN and self.quantity <= 0:
            raise ValidationError({'quantity': 'Stock intake must be positive.'})
        if self.movement_type != self.MovementType.IN and self.quantity >= 0:
            raise ValidationError({'quantity': 'Stock exits must be negative.'})

    def __str__(self):
        return f'{self.lot} - {self.get_movement_type_display()} ({self.quantity})'

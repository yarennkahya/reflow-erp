from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class Business(models.Model):
    class BusinessType(models.TextChoices):
        MARKET = 'market', 'Market'
        RESTAURANT = 'restaurant', 'Restaurant'
        PRODUCER = 'producer', 'Producer'

    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=20, choices=BusinessType.choices)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'businesses'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    class Unit(models.TextChoices):
        PIECE = 'piece', 'Adet'
        KILOGRAM = 'kg', 'Kg'
        LITER = 'liter', 'Litre'

    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100)
    unit = models.CharField(max_length=10, choices=Unit.choices)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name='products',
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
    lot_code = models.CharField(max_length=100)
    expiry_date = models.DateField(db_index=True)
    quantity_received = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
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

    def __str__(self):
        return f'{self.product} ({self.lot_code})'


# NOT: Bilerek MODUL seviyesinde. Nested class'lar (Meta gibi) kardes nested
# class'lara bare isimle erisemez, sadece modul seviyesi isimler otomatik
# gorulur. Bu satirlarin StockMovement'in ICINE tasinmasi eski hataya doner.
class MovementType(models.TextChoices):
    IN = 'IN', 'Stock in'
    OUT_DONATION = 'OUT_DONATION', 'Donation out'
    OUT_SALE = 'OUT_SALE', 'Sale out'
    WASTE = 'WASTE', 'Waste'


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
                            MovementType.OUT_DONATION,
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


class Partner(models.Model):
    name = models.CharField(max_length=255)
    capacity_kg = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0'))],
    )
    contact_email = models.EmailField()
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-capacity_kg', 'name']

    def __str__(self):
        return self.name


# Ayni sebep: MODUL seviyesinde, Distribution'in disinda.
class Channel(models.TextChoices):
    DONATION = 'DONATION', 'Donation'
    DISCOUNT_SALE = 'DISCOUNT_SALE', 'Discount sale'
    WASTE = 'WASTE', 'Waste'


class Distribution(models.Model):
    # Geriye donuk uyumluluk: Distribution.Channel hala calisir.
    Channel = Channel

    lot = models.ForeignKey(
        Lot,
        on_delete=models.PROTECT,
        related_name='distributions',
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    partner = models.ForeignKey(
        Partner,
        on_delete=models.PROTECT,
        related_name='distributions',
        null=True,
        blank=True,
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))],
    )
    decided_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-decided_at', '-pk']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(channel=Channel.DONATION, partner__isnull=False)
                | models.Q(
                    channel__in=[Channel.DISCOUNT_SALE, Channel.WASTE],
                    partner__isnull=True,
                ),
                name='inventory_distribution_partner_matches_channel',
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name='inventory_distribution_quantity_positive',
            ),
        ]

    def clean(self):
        super().clean()
        if self.channel == self.Channel.DONATION and self.partner is None:
            raise ValidationError({'partner': 'A donation requires a partner.'})
        if self.channel != self.Channel.DONATION and self.partner is not None:
            raise ValidationError({'partner': 'Only donations can have a partner.'})

    def __str__(self):
        return f'{self.lot} - {self.get_channel_display()} ({self.quantity})'
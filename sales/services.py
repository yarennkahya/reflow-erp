from django.db import transaction
from django.utils import timezone

from inventory.models import MovementType, StockMovement

from .models import Order


def fulfill_order(order):
    """
    Bir siparisi karsilar: her kalem icin stoktan duser (StockMovement
    OUT_SALE olarak), siparisi FULFILLED isaretler. Hepsi tek transaction --
    production/services.py'deki create_roast_batch ile ayni desen.
    """
    if order.status != Order.Status.PENDING:
        raise ValueError(
            f'Order is not pending (current status: {order.status}).'
        )

    with transaction.atomic():
        for item in order.items.select_related('lot'):
            if item.lot.remaining_quantity < item.quantity:
                raise ValueError(
                    f'Not enough stock in lot {item.lot.lot_code}: '
                    f'need {item.quantity}, have {item.lot.remaining_quantity}.'
                )
                    StockMovement.objects.create(
            lot=output_lot,
            movement_type=MovementType.IN,
            quantity=output_quantity,
        )
        order.status = Order.Status.FULFILLED
        order.fulfilled_at = timezone.now()
        order.save(update_fields=['status', 'fulfilled_at'])
    return order
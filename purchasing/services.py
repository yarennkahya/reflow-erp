from decimal import Decimal

from django.db import transaction

from inventory.models import Lot

from .models import GoodsReceipt, PurchaseOrder


def receive_goods(purchase_order_item, quantity_received, lot_code, expiry_date, warehouse=None):
    """
    Bir satin alma kalemi icin mal teslim alma islemini gerceklestirir.
    Kismi teslimat destekler -- ayni kalem icin birden fazla kez cagrilabilir.
    Her cagri yeni bir Lot ve GoodsReceipt doğurur, unit_cost siparis
    fiyatindan otomatik gelir.
    """
    quantity_received = Decimal(str(quantity_received))
    if quantity_received <= 0:
        raise ValueError('Quantity received must be positive.')
    if quantity_received > purchase_order_item.quantity_remaining:
        raise ValueError(
            f'Cannot receive more than remaining quantity: '
            f'remaining {purchase_order_item.quantity_remaining}, '
            f'trying to receive {quantity_received}.'
        )

    with transaction.atomic():
        lot = Lot.objects.create(
            product=purchase_order_item.product,
            lot_code=lot_code,
            expiry_date=expiry_date,
            quantity_received=quantity_received,
            unit_cost=purchase_order_item.unit_price,
            warehouse=warehouse,
        )
        receipt = GoodsReceipt.objects.create(
            purchase_order_item=purchase_order_item,
            lot=lot,
            quantity_received=quantity_received,
        )

        po = purchase_order_item.purchase_order
        all_items = po.items.all()
        if all(item.quantity_remaining <= 0 for item in all_items):
            po.status = PurchaseOrder.Status.RECEIVED
        else:
            po.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
        po.save(update_fields=['status'])

    return receipt
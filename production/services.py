from decimal import Decimal

from django.db import transaction

from inventory.models import Lot, MovementType, StockMovement

from .models import RoastBatch


def create_roast_batch(*, recipe, input_lots, output_quantity,
                        output_lot_code, output_expiry_date):
    """
    input_lots: {input_product_id: Lot instance} -- her bilesen icin hangi
    spesifik lot'tan tuketilecegini belirtir.
    output_quantity: uretilecek kavrulmus kahve miktari (Decimal-uyumlu).
    """
    output_quantity = Decimal(str(output_quantity))
    if output_quantity <= 0:
        raise ValueError('Output quantity must be positive.')

    components = list(recipe.components.all())
    total_ratio = sum((c.ratio_percent for c in components), Decimal('0'))
    if total_ratio != Decimal('100'):
        raise ValueError(f'Recipe ratios must sum to 100, got {total_ratio}.')

    with transaction.atomic():
        total_input_cost = Decimal('0')
        for component in components:
            lot = input_lots.get(component.input_product_id)
            if lot is None:
                raise ValueError(f'No lot provided for {component.input_product}.')
            needed = (
                output_quantity * component.ratio_percent / Decimal('100')
            ).quantize(Decimal('0.001'))
            if lot.remaining_quantity < needed:
                raise ValueError(
                    f'Not enough stock in lot {lot.lot_code}: '
                    f'need {needed}, have {lot.remaining_quantity}.'
                )
            StockMovement.objects.create(
                lot=lot,
                movement_type=MovementType.OUT_PRODUCTION,
                quantity=-needed,
            )
            total_input_cost += needed * (lot.unit_cost or Decimal('0'))

        output_unit_cost = (total_input_cost / output_quantity).quantize(Decimal('0.01'))

        output_lot = Lot.objects.create(
            product=recipe.output_product,
            lot_code=output_lot_code,
            expiry_date=output_expiry_date,
            quantity_received=output_quantity,
            unit_cost=output_unit_cost,
        )
        batch = RoastBatch.objects.create(
            recipe=recipe,
            output_lot=output_lot,
            total_output_quantity=output_quantity,
        )
    return batch
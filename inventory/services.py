from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import Distribution, Partner, StockMovement


def decide_channel(lot):
    """Return the rule-based channel and partner for a lot without persisting it."""
    days_until_expiry = (lot.expiry_date - timezone.localdate()).days

    if days_until_expiry < 0:
        return Distribution.Channel.WASTE, None

    if days_until_expiry <= 3:
        partner = (
            Partner.objects.filter(is_active=True, capacity_kg__gt=0)
            .order_by('-capacity_kg', 'pk')
            .first()
        )
        if partner is not None:
            return Distribution.Channel.DONATION, partner

    return Distribution.Channel.DISCOUNT_SALE, None


def apply_distribution(lot, quantity):
    """Persist a distribution and its immutable corresponding stock exit together."""
    quantity = Decimal(str(quantity))
    if quantity <= 0:
        raise ValueError('Distribution quantity must be positive.')

    channel, partner = decide_channel(lot)
    movement_type_by_channel = {
        Distribution.Channel.DONATION: StockMovement.MovementType.OUT_DONATION,
        Distribution.Channel.DISCOUNT_SALE: StockMovement.MovementType.OUT_SALE,
        Distribution.Channel.WASTE: StockMovement.MovementType.WASTE,
    }

    with transaction.atomic():
        distribution = Distribution.objects.create(
            lot=lot,
            channel=channel,
            partner=partner,
            quantity=quantity,
        )
        StockMovement.objects.create(
            lot=lot,
            movement_type=movement_type_by_channel[channel],
            quantity=-quantity,
        )

    return distribution

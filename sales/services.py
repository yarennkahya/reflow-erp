from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from audit.services import log_action
from inventory.models import MovementType, Product, StockMovement

from .models import Order, OrderItem


def fulfill_order(order, user=None):
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
                lot=item.lot,
                movement_type=MovementType.OUT_SALE,
                quantity=-item.quantity,
            )
        order.status = Order.Status.FULFILLED
        order.fulfilled_at = timezone.now()
        order.save(update_fields=['status', 'fulfilled_at'])
    log_action(user, 'Sipariş karşılandı', order)
    return order


def get_demand_forecast(product_name, days_ahead=30):
    """
    Son 90 gunluk satis hizina bakarak basit bir talep tahmini uretir
    (hareketli ortalama tabanli, karmasik bir ML modeli degil) ve bunu
    mevcut stokla karsilastirip stogun yetip yetmeyecegini raporlar.
    """
    product = Product.objects.filter(name__icontains=product_name).first()
    if product is None:
        return {'error': f'"{product_name}" adinda bir urun bulunamadi.'}

    lookback_days = 90
    since = timezone.now() - timedelta(days=lookback_days)
    sold = OrderItem.objects.filter(
        product=product,
        order__status='fulfilled',
        order__fulfilled_at__gte=since,
    ).aggregate(total=Sum('quantity'))['total'] or Decimal('0')

    daily_avg = (sold / lookback_days) if sold else Decimal('0')
    forecasted_demand = (daily_avg * days_ahead).quantize(Decimal('0.01'))

    current_stock = sum(
        (lot.remaining_quantity for lot in product.lots.all()), Decimal('0')
    )

    return {
        'product': product.name,
        'lookback_days': lookback_days,
        'total_sold_in_lookback': float(sold),
        'daily_average_sales': float(daily_avg),
        'forecast_days_ahead': days_ahead,
        'forecasted_demand': float(forecasted_demand),
        'current_stock': float(current_stock),
        'stock_sufficient': current_stock >= forecasted_demand,
    }

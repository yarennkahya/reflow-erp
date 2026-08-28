from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from audit.services import log_action
from inventory.models import MovementType, Product, StockMovement
from notifications.services import notify_group

from .models import Order, OrderItem, ReturnRequest


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


def approve_return(return_request, user=None):
    """
    Bir iade talebini onaylar. 'Müşteri vazgeçti' ise urun tek bir IN
    hareketiyle satilabilir stoga geri doner. 'Kusurlu urun' ise once IN
    (fiziksel geri donus) sonra WASTE (satilamaz durumda) olarak iki ayri
    hareket kaydedilir -- net stok degismez ama gercek olay izi korunur.
    """
    if return_request.status != ReturnRequest.Status.REQUESTED:
        raise ValueError('Bu iade talebi zaten sonuçlandırılmış.')
    order_item = return_request.order_item
    if return_request.quantity > order_item.quantity:
        raise ValueError('İade miktarı, satılan miktardan fazla olamaz.')

    with transaction.atomic():
        StockMovement.objects.create(
            lot=order_item.lot,
            movement_type=MovementType.IN,
            quantity=return_request.quantity,
        )
        if return_request.reason == ReturnRequest.Reason.DEFECTIVE:
            StockMovement.objects.create(
                lot=order_item.lot,
                movement_type=MovementType.WASTE,
                quantity=-return_request.quantity,
            )
        return_request.status = ReturnRequest.Status.COMPLETED
        return_request.resolved_at = timezone.now()
        return_request.save(update_fields=['status', 'resolved_at'])
        log_action(user, 'İade onaylandı', return_request)
    return return_request


def reject_return(return_request, user=None):
    """Bir iade talebini reddeder, stokta hiçbir değişiklik yapmaz."""
    if return_request.status != ReturnRequest.Status.REQUESTED:
        raise ValueError('Bu iade talebi zaten sonuçlandırılmış.')
    with transaction.atomic():
        return_request.status = ReturnRequest.Status.REJECTED
        return_request.resolved_at = timezone.now()
        return_request.save(update_fields=['status', 'resolved_at'])
        log_action(user, 'İade reddedildi', return_request)
    return return_request


DEFECTIVE_RETURN_THRESHOLD = 3
DEFECTIVE_RETURN_LOOKBACK_DAYS = 30


def scan_defective_return_patterns():
    """
    Son N gunde bir urunde esik sayida (veya fazla) kusurlu/tamamlanmis
    iade varsa, Uretim & Stok Ekibi'ne bildirim gonderir.
    """
    since = timezone.now() - timedelta(days=DEFECTIVE_RETURN_LOOKBACK_DAYS)
    rows = (
        ReturnRequest.objects.filter(
            reason=ReturnRequest.Reason.DEFECTIVE,
            status=ReturnRequest.Status.COMPLETED,
            resolved_at__gte=since,
        )
        .values('order_item__product')
        .annotate(total=Count('id'))
        .filter(total__gte=DEFECTIVE_RETURN_THRESHOLD)
    )
    flagged = []
    for row in rows:
        product = Product.objects.get(pk=row['order_item__product'])
        notify_group(
            'Üretim & Stok Ekibi',
            f'{product.name} için son {DEFECTIVE_RETURN_LOOKBACK_DAYS} günde '
            f'{row["total"]} kusurlu iade geldi, tarif/tedarikçi gözden '
            f'geçirilmeli.',
            url='/sales/returns/',
        )
        flagged.append(product.pk)
    return {'flagged_products': flagged}

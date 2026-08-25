from decimal import Decimal

from sales.models import Order, OrderItem


def get_profitability_report(start_date=None, end_date=None):
    """
    Belirtilen tarih araligindaki (verilmezse tum zamanlarin) FULFILLED
    siparislerden gelir, maliyet ve kar ozetini hesaplar. Hicbir yeni
    veritabani kaydi olusturmaz -- sales/inventory verisinden anlik
    hesaplanan bir rapordur.
    """
    items = OrderItem.objects.filter(order__status=Order.Status.FULFILLED)
    if start_date:
        items = items.filter(order__fulfilled_at__date__gte=start_date)
    if end_date:
        items = items.filter(order__fulfilled_at__date__lte=end_date)

    total_revenue = Decimal('0')
    total_cost = Decimal('0')
    line_items = []

    for item in items.select_related('lot', 'product', 'order'):
        revenue = item.quantity * item.unit_price
        cost = item.quantity * (item.lot.unit_cost or Decimal('0'))
        total_revenue += revenue
        total_cost += cost
        line_items.append({
            'order_id': item.order_id,
            'product': item.product.name,
            'quantity': float(item.quantity),
            'revenue': float(revenue),
            'cost': float(cost),
            'profit': float(revenue - cost),
        })

    total_profit = total_revenue - total_cost
    margin_percent = (
        (total_profit / total_revenue * 100).quantize(Decimal('0.01'))
        if total_revenue > 0 else Decimal('0')
    )

    return {
        'total_revenue': float(total_revenue),
        'total_cost': float(total_cost),
        'total_profit': float(total_profit),
        'margin_percent': float(margin_percent),
        'line_items': line_items,
    }
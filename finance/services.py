from decimal import Decimal

from django.db import transaction

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


from .models import Invoice, Payment


def create_invoice(order, due_date=None):
    """Karşılanmış bir siparişten fatura oluşturur. Bir siparişin en fazla
    bir faturası olabilir."""
    if hasattr(order, 'invoice'):
        raise ValueError('Bu sipariş için zaten bir fatura oluşturulmuş.')
    if order.status != 'fulfilled':
        raise ValueError('Sadece karşılanmış siparişler için fatura oluşturulabilir.')
    return Invoice.objects.create(order=order, due_date=due_date)


def record_payment(invoice, amount, method):
    """Bir faturaya kısmi veya tam ödeme kaydeder, durumu otomatik günceller.
    purchasing.services.receive_goods ile ayni desen: kismi islem + otomatik
    durum gecisi."""
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError('Ödeme tutarı pozitif olmalı.')
    if amount > invoice.balance_due:
        raise ValueError(
            f'Ödeme, kalan bakiyeden ({invoice.balance_due}) fazla olamaz.'
        )

    with transaction.atomic():
        Payment.objects.create(invoice=invoice, amount=amount, method=method)
        invoice.status = Invoice.Status.PAID if invoice.balance_due <= 0 else Invoice.Status.PARTIALLY_PAID
        invoice.save(update_fields=['status'])
    return invoice

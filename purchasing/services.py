from decimal import Decimal

from django.db import transaction

from audit.services import log_action
from inventory.models import Lot
from notifications.services import notify_group

from .models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem


ORDER_FLOW = [
    PurchaseOrder.Status.DRAFT,
    PurchaseOrder.Status.SENT,
    PurchaseOrder.Status.CONFIRMED,
]


def advance_order_status(purchase_order):
    """Siparişi taslaktan teyide kadar bir sonraki güvenli adıma taşır."""
    if purchase_order.status not in ORDER_FLOW:
        raise ValueError('Bu sipariş bu aşamada ilerletilemez.')
    if purchase_order.status == PurchaseOrder.Status.DRAFT and not purchase_order.items.exists():
        raise ValueError('Siparişi göndermeden önce en az bir sipariş kalemi ekleyin.')

    current_index = ORDER_FLOW.index(purchase_order.status)
    if current_index == len(ORDER_FLOW) - 1:
        raise ValueError('Bu sipariş zaten tedarikçi tarafından teyit edildi.')

    purchase_order.status = ORDER_FLOW[current_index + 1]
    purchase_order.save(update_fields=['status', 'updated_at'])
    return purchase_order


def cancel_purchase_order(purchase_order):
    """Henüz teslim alınmamış siparişi iptal eder."""
    if purchase_order.status in (
        PurchaseOrder.Status.RECEIVED,
        PurchaseOrder.Status.CANCELLED,
    ):
        raise ValueError('Bu sipariş iptal edilemez.')
    if GoodsReceipt.objects.filter(purchase_order_item__purchase_order=purchase_order).exists():
        raise ValueError('Teslim alınmış kalemleri olan sipariş iptal edilemez.')

    purchase_order.status = PurchaseOrder.Status.CANCELLED
    purchase_order.save(update_fields=['status', 'updated_at'])
    return purchase_order


def delete_draft_purchase_order(purchase_order):
    """Teslimatı olmayan taslak siparişi siler."""
    if purchase_order.status != PurchaseOrder.Status.DRAFT:
        raise ValueError('Yalnızca taslak siparişler silinebilir.')
    if GoodsReceipt.objects.filter(purchase_order_item__purchase_order=purchase_order).exists():
        raise ValueError('Teslim kaydı olan sipariş silinemez.')
    purchase_order.delete()


def receive_goods(
    purchase_order_item,
    quantity_received,
    lot_code,
    expiry_date,
    warehouse=None,
    user=None,
):
    """
    Bir satin alma kalemi icin mal teslim alma islemini gerceklestirir.
    Kismi teslimat destekler -- ayni kalem icin birden fazla kez cagrilabilir.
    Her cagri yeni bir Lot ve GoodsReceipt doğurur, unit_cost siparis
    fiyatindan otomatik gelir.
    """
    if purchase_order_item.purchase_order.status not in (
        PurchaseOrder.Status.SENT,
        PurchaseOrder.Status.CONFIRMED,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
    ):
        raise ValueError('Teslim alma için sipariş önce gönderilmeli veya teyit edilmelidir.')

    quantity_received = Decimal(str(quantity_received))
    lot_code = (lot_code or '').strip()
    if quantity_received <= 0:
        raise ValueError('Teslim alınan miktar sıfırdan büyük olmalıdır.')
    if not lot_code:
        raise ValueError('Lot kodu zorunludur.')
    if quantity_received > purchase_order_item.quantity_remaining:
        raise ValueError(
            f'Kalan miktardan fazla teslim alınamaz. '
            f'Kalan: {purchase_order_item.quantity_remaining}, '
            f'girilmiş miktar: {quantity_received}.'
        )

    with transaction.atomic():
        purchase_order_item = PurchaseOrderItem.objects.select_for_update().get(
            pk=purchase_order_item.pk
        )
        if quantity_received > purchase_order_item.quantity_remaining:
            raise ValueError('Bu kalemin kalan miktarı değişti; sayfayı yenileyip tekrar deneyin.')
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
        po.save(update_fields=['status', 'updated_at'])

    log_action(user, 'Mal teslim alındı', receipt)
    return receipt


def check_and_create_reorder(product):
    """
    Bir ürünün toplam stoğu reorder_point'in altındaysa, o ürünün
    tedarikçisine (product.business) otomatik bir TASLAK (draft) satın
    alma siparişi oluşturur. Zaten açık (draft/sent/confirmed/partially_
    received) bir siparişi varsa tekrar oluşturmaz -- çift sipariş
    önlenir. Taslak durumunda olduğu için hiçbir şey otomatik "gönderilmez",
    bir insanın PurchaseOrder'i SENT'e çevirmesi gerekir.
    """
    if product.reorder_point is None or product.reorder_quantity is None:
        return None

    total_stock = sum(
        (lot.remaining_quantity for lot in product.lots.all()), Decimal('0')
    )
    if total_stock >= product.reorder_point:
        return None

    has_open_order = PurchaseOrderItem.objects.filter(
        product=product,
        purchase_order__status__in=['draft', 'sent', 'confirmed', 'partially_received'],
    ).exists()
    if has_open_order:
        return None

    last_item = (
        PurchaseOrderItem.objects.filter(product=product)
        .order_by('-purchase_order__created_at')
        .first()
    )
    unit_price = last_item.unit_price if last_item else Decimal('0')

    with transaction.atomic():
        po = PurchaseOrder.objects.create(supplier=product.business, status='draft')
        PurchaseOrderItem.objects.create(
            purchase_order=po, product=product,
            quantity_ordered=product.reorder_quantity, unit_price=unit_price,
        )
        notify_group(
            'Satın Alma Ekibi',
            f'{product.name} stoğu kritik seviyenin altına düştü '
            f'(kalan: {total_stock}). Otomatik taslak sipariş oluşturuldu: PO #{po.pk}.',
            url=f'/purchasing/orders/{po.pk}/',
        )
    return po

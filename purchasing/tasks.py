from celery import shared_task

from inventory.models import Product

from .services import check_and_create_reorder


@shared_task
def scan_low_stock():
    """
    Her gece çalışır: reorder_point tanımlanmış her ürünü kontrol eder,
    eşiğin altına düşenler için otomatik taslak sipariş oluşturur.
    """
    created = []
    for product in Product.objects.filter(reorder_point__isnull=False):
        po = check_and_create_reorder(product)
        if po:
            created.append(po.pk)
    return {'draft_purchase_orders_created': created}

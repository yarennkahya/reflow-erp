from celery import shared_task
from django.db.models import Sum

from .models import Lot
from .services import apply_distribution


@shared_task
def scan_and_distribute_lots():
    """Her gece çalışır: hâlâ dağıtılmamış miktarı olan her lot için
    kanal kararını verir ve StockMovement + Distribution kaydını oluşturur."""
    created_ids = []
    for lot in Lot.objects.all():
        already_distributed = (
            lot.distributions.aggregate(total=Sum('quantity'))['total'] or 0
        )
        remaining = lot.quantity_received - already_distributed
        if remaining > 0:
            distribution = apply_distribution(lot, remaining)
            created_ids.append(distribution.pk)
    return {'distributions_created': len(created_ids), 'ids': created_ids}
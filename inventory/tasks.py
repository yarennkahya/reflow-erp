from celery import shared_task

from .models import Lot
from .services import get_freshness_status


@shared_task
def scan_lot_freshness():
    """
    Her gece calisir: tum lotlarin tazelik durumunu degerlendirir,
    acil ilgi gerektirenleri raporlar. Otomatik satis/iskarta islemi YAPMAZ --
    bu bilgi ileride AI katmani ve satis modulu tarafindan kullanilacak.
    """
    report = {'NORMAL': 0, 'PRIORITY_SALE': [], 'WASTE': []}
    for lot in Lot.objects.all():
        status = get_freshness_status(lot)
        if status == 'NORMAL':
            report['NORMAL'] += 1
        elif status == 'PRIORITY_SALE':
            report['PRIORITY_SALE'].append(lot.pk)
        else:
            report['WASTE'].append(lot.pk)
    if report['PRIORITY_SALE'] or report['WASTE']:
        from notifications.services import notify_group
        notify_group(
            'Üretim & Stok Ekibi',
            f"Gece taraması: {len(report['PRIORITY_SALE'])} lot acil satış, "
            f"{len(report['WASTE'])} lot ıskarta durumunda.",
            url='/inventory/',
        )
    return report

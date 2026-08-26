from django.utils import timezone

from .models import Product

# SKT'ye/tazelik son tarihine kac gun veya daha az kaldiginda "acele sat" uyarisi versin
PRIORITY_SALE_THRESHOLD_DAYS = 3


def get_freshness_status(lot):
    """
    Bir lot'un tazelik durumunu hesaplar. Hicbir veritabani kaydi OLUSTURMAZ,
    sadece durumu doner: 'NORMAL', 'PRIORITY_SALE', ya da 'WASTE'.
    """
    days_left = (lot.expiry_date - timezone.localdate()).days

    if days_left < 0:
        return 'WASTE'
    if days_left <= PRIORITY_SALE_THRESHOLD_DAYS:
        return 'PRIORITY_SALE'
    return 'NORMAL'


def get_stock_summary(product_name):
    """
    Verilen urun adina (kismi eslesme ile) en yakin Product icin stok ozeti
    doner -- toplam kalan miktar ve her lot'un tazelik durumu dahil.
    AI katmaninin function calling ile cagiracagi ilk gercek 'arac' bu.
    """
    product = Product.objects.filter(name__icontains=product_name).first()
    if product is None:
        return {'error': f'"{product_name}" adinda bir urun bulunamadi.'}

    lots = product.lots.all()
    total_remaining = sum(lot.remaining_quantity for lot in lots)
    lot_details = [
        {
            'lot_code': lot.lot_code,
            'remaining': float(lot.remaining_quantity),
            'expiry_date': str(lot.expiry_date),
            'freshness_status': get_freshness_status(lot),
            'warehouse': lot.warehouse.name if lot.warehouse else 'Belirtilmemiş',
        }
        for lot in lots
    ]
    return {
        'product': product.name,
        'total_remaining': float(total_remaining),
        'unit': product.unit,
        'lots': lot_details,
    }
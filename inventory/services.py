from django.utils import timezone

# SKT'ye/tazelik son tarihine kaç gun veya daha az kaldiginda "acele sat" uyarisi versin
PRIORITY_SALE_THRESHOLD_DAYS = 3


def get_freshness_status(lot):
    """
    Bir lot'un tazelik durumunu hesaplar. Hicbir veritabani kaydi OLUSTURMAZ,
    sadece durumu doner: 'NORMAL', 'PRIORITY_SALE', ya da 'WASTE'.

    Gercek satis islemi ileride 'sales' app'indeki Order akisindan gelecek;
    bu fonksiyon sadece "hangi lot'lara dikkat edilmeli" sorusuna cevap verir.
    """
    days_left = (lot.expiry_date - timezone.localdate()).days

    if days_left < 0:
        return 'WASTE'
    if days_left <= PRIORITY_SALE_THRESHOLD_DAYS:
        return 'PRIORITY_SALE'
    return 'NORMAL'
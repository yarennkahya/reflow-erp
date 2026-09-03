"""View katmanı için küçük paylaşılan yardımcılar."""
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def is_ajax(request):
    """
    base.html'deki AJAX bölge çerçevesinin gönderdiği başlık.

    Önceden her modülde ayrı ayrı kopyalanmıştı (_is_ajax).
    """
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def pick_view(request, allowed, default='list'):
    """?view= parametresini izin verilen görünümlerden birine indirger."""
    requested = request.GET.get('view', default)
    return requested if requested in allowed else default


def paginate(request, objects, per_page=80):
    """
    Odoo control panel'indeki sayfalayıcıyı besler.

    Liste yerine queryset de kabul eder. Sayfa numarası bozuksa ilk/son sayfaya
    düşer, asla 404 vermez.
    """
    paginator = Paginator(objects, per_page)
    try:
        return paginator.page(request.GET.get('page', 1))
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        return paginator.page(paginator.num_pages)


def querystring(request, **overrides):
    """
    Mevcut GET parametrelerini koruyarak bağlantı üretir.

    Görünüm değiştirici ve sayfalayıcı, aktif arama/filtreyi kaybetmemeli.
    None verilen anahtar tamamen düşürülür.
    """
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    # Filtre/görünüm değişince sayfa numarası anlamsızlaşır.
    if 'page' not in overrides:
        params.pop('page', None)
    return params.urlencode()

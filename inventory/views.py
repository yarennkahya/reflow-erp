from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Lot
from .services import get_freshness_status

_FRESHNESS = {
    'NORMAL':        ('bg-success-subtle text-success', 'Normal'),
    'PRIORITY_SALE': ('bg-warning-subtle text-warning',  'Öncelikli Sat'),
    'WASTE':         ('bg-danger-subtle text-danger',   'İade/İmha'),
}


@login_required
def lot_list(request):
    lots_data = []
    for lot in Lot.objects.select_related('product', 'warehouse').order_by('expiry_date'):
        status = get_freshness_status(lot)
        badge_cls, badge_label = _FRESHNESS[status]
        lots_data.append({
            'lot': lot,
            'remaining': lot.remaining_quantity,
            'freshness_cls': badge_cls,
            'freshness_label': badge_label,
        })
    return render(request, 'inventory/list.html', {'lots': lots_data})

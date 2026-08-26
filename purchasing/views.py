from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import PurchaseOrder

_STATUS = {
    'draft':              'bg-secondary-subtle text-secondary',
    'sent':               'bg-info-subtle text-info',
    'confirmed':          'bg-primary-subtle text-primary',
    'partially_received': 'bg-warning-subtle text-warning',
    'received':           'bg-success-subtle text-success',
    'cancelled':          'bg-danger-subtle text-danger',
}


@login_required
def order_list(request):
    orders_data = []
    for po in PurchaseOrder.objects.select_related('supplier').prefetch_related('items').order_by('-created_at'):
        orders_data.append({
            'po': po,
            'item_count': po.items.count(),
            'badge_cls': _STATUS.get(po.status, 'bg-secondary-subtle text-secondary'),
        })
    return render(request, 'purchasing/list.html', {'orders': orders_data})

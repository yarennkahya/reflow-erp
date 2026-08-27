from django.contrib.auth.decorators import login_required
from django.shortcuts import render , get_object_or_404
from inventory.models import Business
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
    response = render(request, 'purchasing/list.html', {'orders': orders_data})
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    return render(request, 'purchasing/order_detail.html', {'order': order})


@login_required
def supplier_list_view(request):
    suppliers = Business.objects.filter(business_type='supplier')
    return render(request, 'purchasing/supplier_list.html', {'suppliers': suppliers})
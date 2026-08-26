from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Order

_STATUS = {
    'pending':   'bg-warning-subtle text-warning',
    'fulfilled': 'bg-success-subtle text-success',
    'cancelled': 'bg-danger-subtle text-danger',
}


@login_required
def order_list(request):
    orders_data = []
    for order in Order.objects.select_related('customer').prefetch_related('items').order_by('-created_at'):
        total = sum(item.quantity * item.unit_price for item in order.items.all())
        orders_data.append({
            'order': order,
            'total': total,
            'badge_cls': _STATUS.get(order.status, 'bg-secondary-subtle text-secondary'),
        })
    return render(request, 'sales/list.html', {'orders': orders_data})

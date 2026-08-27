from django.contrib.auth.decorators import login_required
from django.shortcuts import render , get_object_or_404

from .models import Order , Customer

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

@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'sales/order_detail.html', {'order': order})


@login_required
def customer_list_view(request):
    customers = Customer.objects.all()
    customer_type = request.GET.get('customer_type')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)
    return render(request, 'sales/customer_list.html', {'customers': customers})


@login_required
def customer_detail_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'sales/customer_detail.html', {'customer': customer})
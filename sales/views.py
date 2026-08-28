from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from inventory.models import Product
from .models import Customer, Order, OrderItem, ReturnRequest
from .services import approve_return, get_demand_forecast, reject_return

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


@login_required
def forecast_view(request):
    products_with_sales = Product.objects.filter(
        order_items__order__status='fulfilled'
    ).distinct()
    forecasts = [get_demand_forecast(p.name) for p in products_with_sales]
    return render(request, 'sales/forecast.html', {'forecasts': forecasts})


@login_required
def return_list_view(request):
    return_requests = ReturnRequest.objects.select_related(
        'order_item__order__customer', 'order_item__product'
    ).order_by('-requested_at')
    return render(request, 'sales/return_list.html', {
        'return_requests': return_requests,
    })


@login_required
@require_POST
def return_request_create_view(request, item_pk):
    order_item = get_object_or_404(OrderItem, pk=item_pk)
    ReturnRequest.objects.create(
        order_item=order_item,
        reason=request.POST.get('reason'),
        quantity=request.POST.get('quantity'),
    )
    return redirect('order-detail', pk=order_item.order_id)


@login_required
@require_POST
def return_approve_view(request, pk):
    return_request = get_object_or_404(ReturnRequest, pk=pk)
    try:
        approve_return(return_request, user=request.user)
    except ValueError:
        pass
    return redirect('return-list')


@login_required
@require_POST
def return_reject_view(request, pk):
    return_request = get_object_or_404(ReturnRequest, pk=pk)
    try:
        reject_return(return_request, user=request.user)
    except ValueError:
        pass
    return redirect('return-list')

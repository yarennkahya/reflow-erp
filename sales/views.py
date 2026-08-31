from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from inventory.models import Lot, Product
from .models import Customer, Order, OrderItem, ReturnRequest
from .services import approve_return, fulfill_order, get_demand_forecast, reject_return

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


@login_required
def order_create_view(request):
    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=request.POST['customer'])
        order = Order.objects.create(customer=customer)

        products = request.POST.getlist('product')
        lots = request.POST.getlist('lot')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('unit_price')

        for product_id, lot_id, qty, price in zip(products, lots, quantities, prices):
            if not (product_id and lot_id and qty and price):
                continue
            OrderItem.objects.create(
                order=order,
                product_id=product_id,
                lot_id=lot_id,
                quantity=qty,
                unit_price=price,
            )

        if not order.items.exists():
            order.delete()
            messages.error(request, 'En az bir kalem eklemelisiniz.')
            return redirect('sales-list')

        if request.POST.get('fulfill_now'):
            try:
                fulfill_order(order)
                messages.success(request, 'Sipariş oluşturuldu ve karşılandı.')
            except ValueError as exc:
                messages.warning(
                    request,
                    f'Sipariş oluşturuldu ama karşılanamadı: {exc}',
                )
        else:
            messages.success(
                request,
                'Sipariş taslak olarak oluşturuldu (henüz karşılanmadı).',
            )

        return redirect('order-detail', pk=order.pk)

    return render(request, 'sales/order_form.html', {
        'customers': Customer.objects.all(),
        'products': Product.objects.all(),
        'lots': Lot.objects.select_related('product').all(),
    })

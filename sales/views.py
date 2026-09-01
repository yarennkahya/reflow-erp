from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from dashboard.grouping import group_by_choice
from dashboard.views_helpers import is_ajax, paginate, pick_view
from inventory.models import Lot, Product

from .forms import CustomerForm
from .models import Customer, Order, OrderItem, ReturnRequest
from .services import (
    approve_return,
    cancel_order,
    fulfill_order,
    get_demand_forecast,
    reject_return,
    set_order_status,
)

@login_required
def order_list(request):
    orders = (Order.objects
              .select_related('customer', 'invoice')
              .prefetch_related('items'))
    query = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', 'all')

    if selected_status in Order.Status.values:
        orders = orders.filter(status=selected_status)
    else:
        selected_status = 'all'
    if query:
        search = Q(customer__name__icontains=query)
        if query.isdigit():
            search |= Q(pk=int(query))
        orders = orders.filter(search)

    rows = [
        {
            'order': order,
            'total': sum((item.line_total for item in order.items.all()), Decimal('0')),
            'item_count': order.items.count(),
        }
        for order in orders.order_by('-created_at')
    ]

    view = pick_view(request, ('list', 'kanban'))
    page_obj = paginate(request, rows) if view == 'list' else None

    return render(request, 'sales/list.html', {
        'view': view,
        'view_template': f'sales/_orders_{view}.html',
        'page_obj': page_obj,
        'orders': list(page_obj) if page_obj is not None else rows,
        'columns': (
            group_by_choice(
                rows, 'status', Order.Status.choices,
                key=lambda row: row['order'].status,
                aggregate=lambda row: float(row['total']),
            ) if view == 'kanban' else None
        ),
        'query': query,
        'selected_status': selected_status,
        'status_choices': Order.Status.choices,
        'pending_count': Order.objects.filter(status=Order.Status.PENDING).count(),
        'fulfilled_count': Order.objects.filter(status=Order.Status.FULFILLED).count(),
        'cancelled_count': Order.objects.filter(status=Order.Status.CANCELLED).count(),
    })


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(Order, pk=pk)
    return render(request, 'sales/order_detail.html', {'order': order})


@login_required
def customer_list_view(request):
    customers = Customer.objects.all()
    query = request.GET.get('q', '').strip()
    # Eskiden seçili filtre context'e geri verilmiyordu; dropdown mevcut
    # seçimi gösteremiyordu.
    selected_type = request.GET.get('customer_type', 'all')

    if selected_type in Customer.CustomerType.values:
        customers = customers.filter(customer_type=selected_type)
    else:
        selected_type = 'all'
    if query:
        customers = customers.filter(
            Q(name__icontains=query)
            | Q(contact_email__icontains=query)
            | Q(contact_phone__icontains=query)
        )

    page_obj = paginate(request, customers.order_by('name'))
    return render(request, 'sales/customer_list.html', {
        'page_obj': page_obj,
        'customers': page_obj,
        'query': query,
        'selected_type': selected_type,
        'type_choices': Customer.CustomerType.choices,
        'total_customers': Customer.objects.count(),
        'wholesale_count': Customer.objects.filter(
            customer_type=Customer.CustomerType.WHOLESALE).count(),
    })


@login_required
def customer_detail_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'sales/customer_detail.html', {'customer': customer})


@login_required
def forecast_view(request):
    products_with_sales = Product.objects.filter(
        order_items__order__status=Order.Status.FULFILLED
    ).distinct()
    forecasts = [get_demand_forecast(p.name) for p in products_with_sales]
    # Hatalı satırları şablon yerine burada ayıklıyoruz.
    valid = [f for f in forecasts if not f.get('error')]

    view = pick_view(request, ('list', 'graph'))
    chart = None
    if view == 'graph' and valid:
        chart = {
            'labels': [f['product'] for f in valid],
            'datasets': [
                {'label': str(_('Tahmini talep')), 'data': [f['forecasted_demand'] for f in valid]},
                {'label': str(_('Mevcut stok')), 'data': [f['current_stock'] for f in valid]},
            ],
        }

    return render(request, 'sales/forecast.html', {
        'view': view,
        'forecasts': valid,
        'error_count': len(forecasts) - len(valid),
        'chart': chart,
        'insufficient': sum(1 for f in valid if not f['stock_sufficient']),
    })


@login_required
def return_list_view(request):
    returns = ReturnRequest.objects.select_related(
        'order_item__order__customer', 'order_item__product'
    )
    selected_status = request.GET.get('status', 'all')
    if selected_status in ReturnRequest.Status.values:
        returns = returns.filter(status=selected_status)
    else:
        selected_status = 'all'

    page_obj = paginate(request, returns.order_by('-requested_at'))
    return render(request, 'sales/return_list.html', {
        'page_obj': page_obj,
        'return_requests': page_obj,
        'selected_status': selected_status,
        'status_choices': ReturnRequest.Status.choices,
        'pending_returns': ReturnRequest.objects.filter(
            status=ReturnRequest.Status.REQUESTED).count(),
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
        'selected_customer_id': request.GET.get('customer', ''),
        'customers': Customer.objects.all(),
        'products': Product.objects.all(),
        'lots': Lot.objects.select_related('product').all(),
    })


@login_required
@require_POST
def order_set_status_view(request, pk):
    """
    Hem kanban sürükle-bırak hem de sipariş detayındaki aksiyon butonları
    buraya gelir. AJAX ise JSON döner (JS kartı geri alabilsin diye hatada
    400), normal form gönderimiyse mesaj bırakıp geri yönlendirir.
    """
    order = get_object_or_404(Order, pk=pk)
    ajax = is_ajax(request)
    try:
        set_order_status(order, request.POST.get('stage', ''), user=request.user)
    except ValueError as error:
        if ajax:
            return JsonResponse({'ok': False, 'error': str(error)}, status=400)
        messages.error(request, str(error))
    else:
        if ajax:
            return JsonResponse({'ok': True})
        messages.success(
            request,
            f'Sipariş #{order.pk} → {order.get_status_display()}',
        )
    return redirect(request.POST.get('next') or 'order-detail', pk=order.pk)


@login_required
def customer_create_view(request):
    """
    Yeni musteri.

    ?next= ile geldiyse (or. sipariş formundaki "yeni müşteri ekle"), kayittan
    sonra oraya doner ve yeni musteriyi ?customer= ile onceden secili birakir.
    purchasing.order_create'in tedarikci akisiyla ayni desen.
    """
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save()
        messages.success(request, f'{customer.name} müşterisi eklendi.')
        next_url = request.POST.get('next') or request.GET.get('next')
        if next_url:
            separator = '&' if '?' in next_url else '?'
            return redirect(f'{next_url}{separator}customer={customer.pk}')
        return redirect('customer-detail', pk=customer.pk)
    return render(request, 'sales/customer_form.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


@login_required
def customer_edit_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Müşteri bilgileri güncellendi.')
        return redirect('customer-detail', pk=customer.pk)
    return render(request, 'sales/customer_form.html', {
        'form': form,
        'customer': customer,
    })

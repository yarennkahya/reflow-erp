from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from inventory.models import Business, Product

from .forms import (
    GoodsReceiptForm,
    PurchaseOrderForm,
    PurchaseOrderItemForm,
    SupplierForm,
    SupplierProductForm,
)
from .models import GoodsReceipt, PurchaseOrder, PurchaseOrderItem
from .services import (
    advance_order_status,
    cancel_purchase_order,
    delete_draft_purchase_order,
    receive_goods,
)


STATUS_CLASSES = {
    PurchaseOrder.Status.DRAFT: 'status-draft',
    PurchaseOrder.Status.SENT: 'status-sent',
    PurchaseOrder.Status.CONFIRMED: 'status-confirmed',
    PurchaseOrder.Status.PARTIALLY_RECEIVED: 'status-partially_received',
    PurchaseOrder.Status.RECEIVED: 'status-received',
    PurchaseOrder.Status.CANCELLED: 'status-cancelled',
}


def _order_rows(orders):
    """Şablon için prefetched kalemlerden sipariş özetlerini hesaplar."""
    rows = []
    for order in orders:
        items = list(order.items.all())
        rows.append({
            'order': order,
            'item_count': len(items),
            'total': sum((item.line_total for item in items), Decimal('0')),
            'status_class': STATUS_CLASSES.get(order.status, 'status-draft'),
            'is_overdue': bool(
                order.expected_delivery_date
                and order.expected_delivery_date < timezone.localdate()
                and order.status in (
                    PurchaseOrder.Status.SENT,
                    PurchaseOrder.Status.CONFIRMED,
                    PurchaseOrder.Status.PARTIALLY_RECEIVED,
                )
            ),
        })
    return rows


@login_required
def order_list(request):
    selected_status = request.GET.get('status', 'all')
    query = request.GET.get('q', '').strip()

    orders = PurchaseOrder.objects.select_related('supplier').prefetch_related('items')
    if selected_status in PurchaseOrder.Status.values:
        orders = orders.filter(status=selected_status)
    else:
        selected_status = 'all'
    if query:
        search_filter = Q(supplier__name__icontains=query) | Q(notes__icontains=query)
        if query.isdigit():
            search_filter |= Q(pk=int(query))
        orders = orders.filter(search_filter)

    today = timezone.localdate()
    open_statuses = (
        PurchaseOrder.Status.DRAFT,
        PurchaseOrder.Status.SENT,
        PurchaseOrder.Status.CONFIRMED,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
    )
    overdue_orders = PurchaseOrder.objects.filter(
        expected_delivery_date__lt=today,
        status__in=(
            PurchaseOrder.Status.SENT,
            PurchaseOrder.Status.CONFIRMED,
            PurchaseOrder.Status.PARTIALLY_RECEIVED,
        ),
    )

    response = render(request, 'purchasing/list.html', {
        'orders': _order_rows(orders.order_by('-created_at')),
        'query': query,
        'selected_status': selected_status,
        'status_choices': PurchaseOrder.Status.choices,
        'open_order_count': PurchaseOrder.objects.filter(status__in=open_statuses).count(),
        'awaiting_delivery_count': PurchaseOrder.objects.filter(
            status__in=(PurchaseOrder.Status.SENT, PurchaseOrder.Status.CONFIRMED)
        ).count(),
        'overdue_count': overdue_orders.count(),
    })
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


@login_required
def order_create(request):
    initial = {}
    supplier_id = request.GET.get('supplier')
    if supplier_id and supplier_id.isdigit() and Business.objects.filter(
        pk=supplier_id,
        business_type=Business.BusinessType.SUPPLIER,
        is_active=True,
    ).exists():
        initial['supplier'] = supplier_id

    form = PurchaseOrderForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        order = form.save()
        messages.success(request, 'Taslak satın alma siparişi oluşturuldu. Şimdi sipariş kalemlerini ekleyin.')
        return redirect('purchase-order-detail', pk=order.pk)
    return render(request, 'purchasing/order_form.html', {'form': form, 'order': None})


@login_required
def order_detail_view(request, pk):
    order = get_object_or_404(
        PurchaseOrder.objects.select_related('supplier').prefetch_related(
            'items__product', 'items__goods_receipts__lot__warehouse'
        ),
        pk=pk,
    )

    item_rows = []
    for item in order.items.all():
        receipts = list(item.goods_receipts.all())
        received = sum((receipt.quantity_received for receipt in receipts), Decimal('0'))
        remaining = item.quantity_ordered - received
        progress = int((received / item.quantity_ordered) * 100) if item.quantity_ordered else 0
        item_rows.append({
            'item': item,
            'received': received,
            'remaining': remaining,
            'progress': min(progress, 100),
            'receipts': receipts,
        })

    receipts = GoodsReceipt.objects.filter(
        purchase_order_item__purchase_order=order
    ).select_related('purchase_order_item__product', 'lot__warehouse').order_by('-received_at')

    return render(request, 'purchasing/order_detail.html', {
        'order': order,
        'items': item_rows,
        'receipts': receipts,
        'status_class': STATUS_CLASSES.get(order.status, 'status-draft'),
        'item_count': len(item_rows),
        'total': sum((row['item'].line_total for row in item_rows), Decimal('0')),
        'can_advance': (
            order.status == PurchaseOrder.Status.SENT
            or (
                order.status == PurchaseOrder.Status.DRAFT
                and bool(item_rows)
            )
        ),
        'can_cancel': order.status not in (
            PurchaseOrder.Status.RECEIVED,
            PurchaseOrder.Status.CANCELLED,
        ),
    })


@login_required
def order_edit(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    if not order.is_editable:
        messages.error(request, 'Sipariş bilgileri yalnızca taslak aşamasında düzenlenebilir.')
        return redirect('purchase-order-detail', pk=order.pk)

    form = PurchaseOrderForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Sipariş bilgileri güncellendi.')
        return redirect('purchase-order-detail', pk=order.pk)
    return render(request, 'purchasing/order_form.html', {'form': form, 'order': order})


@login_required
@require_POST
def order_advance(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        advance_order_status(order)
        messages.success(request, f'Sipariş “{order.get_status_display()}” aşamasına taşındı.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('purchase-order-detail', pk=order.pk)


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        cancel_purchase_order(order)
        messages.success(request, 'Sipariş iptal edildi.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('purchase-order-detail', pk=order.pk)


@login_required
@require_POST
def order_delete(request, pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    try:
        delete_draft_purchase_order(order)
        messages.success(request, 'Taslak satın alma siparişi silindi.')
        return redirect('purchasing-list')
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('purchase-order-detail', pk=order.pk)


@login_required
def order_item_create(request, pk):
    order = get_object_or_404(PurchaseOrder.objects.select_related('supplier'), pk=pk)
    if not order.is_editable:
        messages.error(request, 'Sipariş kalemleri yalnızca taslak aşamasında değiştirilebilir.')
        return redirect('purchase-order-detail', pk=order.pk)

    form = PurchaseOrderItemForm(request.POST or None, purchase_order=order)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.purchase_order = order
        item.save()
        messages.success(request, 'Sipariş kalemi eklendi.')
        return redirect('purchase-order-detail', pk=order.pk)
    return render(request, 'purchasing/order_item_form.html', {
        'form': form,
        'order': order,
        'item': None,
        'has_catalog_products': order.supplier.products.exists(),
    })


@login_required
def order_item_edit(request, pk, item_pk):
    order = get_object_or_404(PurchaseOrder.objects.select_related('supplier'), pk=pk)
    item = get_object_or_404(PurchaseOrderItem, pk=item_pk, purchase_order=order)
    if not order.is_editable:
        messages.error(request, 'Sipariş kalemleri yalnızca taslak aşamasında değiştirilebilir.')
        return redirect('purchase-order-detail', pk=order.pk)

    form = PurchaseOrderItemForm(
        request.POST or None,
        instance=item,
        purchase_order=order,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Sipariş kalemi güncellendi.')
        return redirect('purchase-order-detail', pk=order.pk)
    return render(request, 'purchasing/order_item_form.html', {
        'form': form,
        'order': order,
        'item': item,
        'has_catalog_products': order.supplier.products.exists(),
    })


@login_required
@require_POST
def order_item_delete(request, pk, item_pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(PurchaseOrderItem, pk=item_pk, purchase_order=order)
    if not order.is_editable:
        messages.error(request, 'Sipariş kalemleri yalnızca taslak aşamasında silinebilir.')
    else:
        item.delete()
        messages.success(request, 'Sipariş kalemi silindi.')
    return redirect('purchase-order-detail', pk=order.pk)


@login_required
def order_item_receive(request, pk, item_pk):
    order = get_object_or_404(PurchaseOrder, pk=pk)
    item = get_object_or_404(
        PurchaseOrderItem.objects.select_related('product', 'purchase_order'),
        pk=item_pk,
        purchase_order=order,
    )
    if not order.is_receivable:
        messages.error(request, 'Bu sipariş henüz teslim almaya uygun durumda değil.')
        return redirect('purchase-order-detail', pk=order.pk)

    remaining = item.quantity_remaining
    if remaining <= 0:
        messages.info(request, 'Bu sipariş kalemi zaten tamamen teslim alındı.')
        return redirect('purchase-order-detail', pk=order.pk)

    form = GoodsReceiptForm(request.POST or None, initial={'quantity_received': remaining})
    if request.method == 'POST' and form.is_valid():
        try:
            receive_goods(
                item,
                quantity_received=form.cleaned_data['quantity_received'],
                lot_code=form.cleaned_data['lot_code'],
                expiry_date=form.cleaned_data['expiry_date'],
                warehouse=form.cleaned_data['warehouse'],
            )
            messages.success(request, 'Teslim alma kaydedildi ve stok lotu oluşturuldu.')
            return redirect('purchase-order-detail', pk=order.pk)
        except (ValueError, IntegrityError) as error:
            form.add_error(None, str(error))

    return render(request, 'purchasing/receipt_form.html', {
        'form': form,
        'order': order,
        'item': item,
        'remaining': remaining,
    })


@login_required
def supplier_list_view(request):
    query = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', 'active')
    suppliers = Business.objects.filter(business_type=Business.BusinessType.SUPPLIER)
    if selected_status == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif selected_status == 'inactive':
        suppliers = suppliers.filter(is_active=False)
    else:
        selected_status = 'all'
    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query)
            | Q(contact_email__icontains=query)
            | Q(contact_phone__icontains=query)
        )

    suppliers = suppliers.annotate(
        order_count=Count('purchase_orders', distinct=True),
        open_order_count=Count(
            'purchase_orders',
            filter=Q(purchase_orders__status__in=(
                PurchaseOrder.Status.DRAFT,
                PurchaseOrder.Status.SENT,
                PurchaseOrder.Status.CONFIRMED,
                PurchaseOrder.Status.PARTIALLY_RECEIVED,
            )),
            distinct=True,
        ),
    ).order_by('-is_active', 'name')

    return render(request, 'purchasing/supplier_list.html', {
        'suppliers': suppliers,
        'query': query,
        'selected_status': selected_status,
        'supplier_count': Business.objects.filter(
            business_type=Business.BusinessType.SUPPLIER
        ).count(),
        'active_supplier_count': Business.objects.filter(
            business_type=Business.BusinessType.SUPPLIER,
            is_active=True,
        ).count(),
    })


@login_required
def supplier_create(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        supplier = form.save(commit=False)
        supplier.business_type = Business.BusinessType.SUPPLIER
        supplier.save()
        messages.success(request, f'{supplier.name} tedarikçisi eklendi.')
        return redirect('supplier-detail', pk=supplier.pk)
    return render(request, 'purchasing/supplier_form.html', {'form': form, 'supplier': None})


@login_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    orders = list(
        supplier.purchase_orders.prefetch_related('items').order_by('-created_at')
    )
    order_rows = _order_rows(orders)
    products = supplier.products.all()

    return render(request, 'purchasing/supplier_detail.html', {
        'supplier': supplier,
        'orders': order_rows,
        'products': products,
        'open_order_count': sum(
            row['order'].status not in (
                PurchaseOrder.Status.RECEIVED,
                PurchaseOrder.Status.CANCELLED,
            ) for row in order_rows
        ),
        'total_order_value': sum((row['total'] for row in order_rows), Decimal('0')),
    })


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tedarikçi bilgileri güncellendi.')
        return redirect('supplier-detail', pk=supplier.pk)
    return render(request, 'purchasing/supplier_form.html', {
        'form': form,
        'supplier': supplier,
    })


@login_required
@require_POST
def supplier_activity(request, pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    supplier.is_active = not supplier.is_active
    supplier.save(update_fields=['is_active'])
    state = 'aktif' if supplier.is_active else 'pasif'
    messages.success(request, f'{supplier.name} tedarikçisi {state} duruma alındı.')
    return redirect('supplier-detail', pk=supplier.pk)


@login_required
@require_POST
def supplier_delete(request, pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    supplier_name = supplier.name
    try:
        supplier.delete()
    except ProtectedError:
        messages.error(
            request,
            'Bu tedarikçiye bağlı ürün veya satın alma geçmişi var. Geçmişi korumak için silinemez; tedarikçiyi pasife alabilirsiniz.',
        )
        return redirect('supplier-detail', pk=supplier.pk)

    messages.success(request, f'{supplier_name} tedarikçisi silindi.')
    return redirect('supplier-list')


@login_required
def supplier_product_create(request, pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    form = SupplierProductForm(request.POST or None, supplier=supplier)
    form.instance.business = supplier
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f'{product.name} ürününü tedarikçi kataloğuna eklediniz.')
        return redirect('supplier-detail', pk=supplier.pk)
    return render(request, 'purchasing/supplier_product_form.html', {
        'form': form,
        'supplier': supplier,
        'product': None,
    })


@login_required
def supplier_product_edit(request, pk, product_pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    product = get_object_or_404(Product, pk=product_pk, business=supplier)
    form = SupplierProductForm(
        request.POST or None,
        instance=product,
        supplier=supplier,
    )
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Tedarikçi ürün bilgisi güncellendi.')
        return redirect('supplier-detail', pk=supplier.pk)
    return render(request, 'purchasing/supplier_product_form.html', {
        'form': form,
        'supplier': supplier,
        'product': product,
    })


@login_required
@require_POST
def supplier_product_delete(request, pk, product_pk):
    supplier = get_object_or_404(
        Business.objects.filter(business_type=Business.BusinessType.SUPPLIER),
        pk=pk,
    )
    product = get_object_or_404(Product, pk=product_pk, business=supplier)
    try:
        product.delete()
    except ProtectedError:
        messages.error(
            request,
            'Bu ürün sipariş veya stok geçmişinde kullanıldığı için silinemez.',
        )
    else:
        messages.success(request, 'Tedarikçi ürünü silindi.')
    return redirect('supplier-detail', pk=supplier.pk)

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum, Value
from django.db.models.deletion import ProtectedError
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import WarehouseForm
from .models import Lot, MovementType, Warehouse
from .services import get_freshness_status


FRESHNESS = {
    'NORMAL': ('freshness-normal', 'Normal'),
    'PRIORITY_SALE': ('freshness-priority_sale', 'Öncelikli kullanım'),
    'WASTE': ('freshness-waste', 'SKT geçti'),
}

MOVEMENT_META = {
    MovementType.IN: ('Stok girişi', 'movement-in', 'bi-box-arrow-in-down'),
    MovementType.OUT_PRODUCTION: ('Üretimde kullanıldı', 'movement-production', 'bi-fire'),
    MovementType.OUT_SALE: ('Satış sevkiyatı', 'movement-sale', 'bi-cart-check'),
    MovementType.WASTE: ('İmha / zayi', 'movement-waste', 'bi-trash3'),
}


def _with_remaining_quantity(queryset):
    movement_total = Coalesce(
        Sum('stock_movements__quantity'),
        Value(Decimal('0.000')),
        output_field=DecimalField(max_digits=12, decimal_places=3),
    )
    return queryset.annotate(
        current_quantity=ExpressionWrapper(
            F('quantity_received') + movement_total,
            output_field=DecimalField(max_digits=12, decimal_places=3),
        )
    ).select_related('product', 'warehouse', 'product__business')


def _lot_rows(lots):
    rows = []
    for lot in lots:
        freshness = get_freshness_status(lot)
        freshness_class, freshness_label = FRESHNESS[freshness]
        remaining = lot.current_quantity
        rows.append({
            'lot': lot,
            'remaining': remaining,
            'freshness': freshness,
            'freshness_class': freshness_class,
            'freshness_label': freshness_label,
            'is_empty': remaining <= 0,
        })
    return rows


@login_required
def lot_list(request):
    query = request.GET.get('q', '').strip()
    selected_warehouse = request.GET.get('warehouse', 'all')
    selected_freshness = request.GET.get('freshness', 'all')

    lots = Lot.objects.all()
    if query:
        lots = lots.filter(
            Q(product__name__icontains=query)
            | Q(lot_code__icontains=query)
            | Q(product__category__icontains=query)
        )
    if selected_warehouse == 'unassigned':
        lots = lots.filter(warehouse__isnull=True)
    elif selected_warehouse.isdigit():
        lots = lots.filter(warehouse_id=int(selected_warehouse))
    else:
        selected_warehouse = 'all'

    rows = _lot_rows(_with_remaining_quantity(lots).order_by('expiry_date', 'lot_code'))
    if selected_freshness in FRESHNESS:
        rows = [row for row in rows if row['freshness'] == selected_freshness]
    else:
        selected_freshness = 'all'

    return render(request, 'inventory/list.html', {
        'lots': rows,
        'query': query,
        'selected_warehouse': selected_warehouse,
        'selected_freshness': selected_freshness,
        'warehouses': Warehouse.objects.all(),
        'total_lots': len(rows),
        'available_lots': sum(not row['is_empty'] for row in rows),
        'unassigned_lots': sum(row['lot'].warehouse_id is None for row in rows),
        'attention_lots': sum(
            row['freshness'] != 'NORMAL' and not row['is_empty'] for row in rows
        ),
    })


@login_required
def lot_detail(request, pk):
    lot = get_object_or_404(
        Lot.objects.select_related(
            'product',
            'product__business',
            'warehouse',
            'goods_receipt__purchase_order_item__purchase_order',
            'produced_by_batch__recipe',
        ),
        pk=pk,
    )
    movements = []
    for movement in lot.stock_movements.all().order_by('-created_at', '-pk'):
        label, css_class, icon = MOVEMENT_META.get(
            movement.movement_type,
            (movement.get_movement_type_display(), 'movement-in', 'bi-arrow-left-right'),
        )
        movements.append({
            'movement': movement,
            'label': label,
            'css_class': css_class,
            'icon': icon,
        })

    freshness = get_freshness_status(lot)
    freshness_class, freshness_label = FRESHNESS[freshness]
    if hasattr(lot, 'goods_receipt'):
        receipt = lot.goods_receipt
        order = receipt.purchase_order_item.purchase_order
        stock_source = {
            'label': f'PO #{order.pk}',
            'description': f'{order.supplier.name} teslim alımı',
            'url': reverse('purchase-order-detail', args=[order.pk]),
            'icon': 'bi-basket3',
        }
    elif hasattr(lot, 'produced_by_batch'):
        batch = lot.produced_by_batch
        stock_source = {
            'label': 'Kavurma partisi',
            'description': batch.recipe.name,
            'url': reverse('production-batch-detail', args=[batch.pk]),
            'icon': 'bi-fire',
        }
    else:
        stock_source = {
            'label': 'İlk stok kaydı',
            'description': 'Geçmişte oluşturulmuş lot kaydı',
            'url': None,
            'icon': 'bi-box-seam',
        }
    return render(request, 'inventory/lot_detail.html', {
        'lot': lot,
        'remaining': lot.remaining_quantity,
        'freshness': freshness,
        'freshness_class': freshness_class,
        'freshness_label': freshness_label,
        'movements': movements,
        'stock_source': stock_source,
    })


@login_required
def warehouse_list(request):
    query = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', 'active')

    warehouses = Warehouse.objects.annotate(lot_count=Count('lots', distinct=True))
    if selected_status == 'active':
        warehouses = warehouses.filter(is_active=True)
    elif selected_status == 'inactive':
        warehouses = warehouses.filter(is_active=False)
    else:
        selected_status = 'all'
    if query:
        warehouses = warehouses.filter(
            Q(name__icontains=query) | Q(city__icontains=query)
        )

    return render(request, 'inventory/warehouse_list.html', {
        'warehouses': warehouses.order_by('-is_active', 'name'),
        'query': query,
        'selected_status': selected_status,
        'warehouse_count': Warehouse.objects.count(),
        'active_warehouse_count': Warehouse.objects.filter(is_active=True).count(),
    })


@login_required
def warehouse_create(request):
    form = WarehouseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        warehouse = form.save()
        messages.success(request, f'{warehouse.name} deposu eklendi.')
        return redirect('warehouse-detail', pk=warehouse.pk)
    return render(request, 'inventory/warehouse_form.html', {
        'form': form,
        'warehouse': None,
    })


@login_required
def warehouse_detail(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    rows = _lot_rows(
        _with_remaining_quantity(warehouse.lots.all()).order_by('expiry_date', 'lot_code')
    )
    return render(request, 'inventory/warehouse_detail.html', {
        'warehouse': warehouse,
        'lots': rows,
        'lot_count': len(rows),
        'available_lots': sum(not row['is_empty'] for row in rows),
        'attention_lots': sum(
            row['freshness'] != 'NORMAL' and not row['is_empty'] for row in rows
        ),
    })


@login_required
def warehouse_edit(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    form = WarehouseForm(request.POST or None, instance=warehouse)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Depo bilgileri güncellendi.')
        return redirect('warehouse-detail', pk=warehouse.pk)
    return render(request, 'inventory/warehouse_form.html', {
        'form': form,
        'warehouse': warehouse,
    })


@login_required
@require_POST
def warehouse_activity(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    warehouse.is_active = not warehouse.is_active
    warehouse.save(update_fields=['is_active'])
    status = 'aktif' if warehouse.is_active else 'pasif'
    messages.success(request, f'{warehouse.name} deposu {status} duruma alındı.')
    return redirect('warehouse-detail', pk=warehouse.pk)


@login_required
@require_POST
def warehouse_delete(request, pk):
    warehouse = get_object_or_404(Warehouse, pk=pk)
    warehouse_name = warehouse.name
    try:
        warehouse.delete()
    except ProtectedError:
        messages.error(
            request,
            'Bu depoda lot kaydı var. Stok geçmişini korumak için silinemez; depoyu pasife alabilirsiniz.',
        )
        return redirect('warehouse-detail', pk=warehouse.pk)

    messages.success(request, f'{warehouse_name} deposu silindi.')
    return redirect('warehouse-list')

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from sales.models import Customer

from .forms import CustomerForm, SaleForm
from .models import Opportunity
from .services import advance_stage, mark_as_lost, set_sale_activity

@login_required
def customer_list(request):
    query = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', 'active')

    customers = Customer.objects.all()
    if selected_status == 'active':
        customers = customers.filter(is_active=True)
    elif selected_status == 'inactive':
        customers = customers.filter(is_active=False)
    else:
        selected_status = 'all'

    if query:
        customers = customers.filter(
            Q(name__icontains=query)
            | Q(contact_email__icontains=query)
            | Q(contact_phone__icontains=query)
        )

    customers = customers.annotate(
        sale_count=Count('opportunities', distinct=True),
        active_sale_count=Count(
            'opportunities',
            filter=Q(opportunities__status=Opportunity.Status.ACTIVE),
            distinct=True,
        ),
    ).order_by('-is_active', 'name')

    context = {
        'customers': customers,
        'query': query,
        'selected_status': selected_status,
        'total_customers': Customer.objects.count(),
        'active_customers': Customer.objects.filter(is_active=True).count(),
        'active_sales': Opportunity.objects.filter(status=Opportunity.Status.ACTIVE).count(),
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'crm/partials/customer_list_region.html', context)
    return render(request, 'crm/list.html', context)


@login_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save()
        messages.success(request, f'{customer.name} müşterisi eklendi.')
        return redirect('crm-customer-detail', pk=customer.pk)
    return render(request, 'crm/customer_form.html', {'form': form, 'customer': None})


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    sales = list(customer.opportunities.all().order_by('-updated_at'))
    orders = customer.orders.all().order_by('-created_at')

    return render(request, 'crm/customer_detail.html', {
        'customer': customer,
        'sales': sales,
        'orders': orders,
        'sale_count': len(sales),
        'active_sale_count': sum(
            sale.status == Opportunity.Status.ACTIVE for sale in sales
        ),
        'estimated_total': sum(sale.estimated_value or 0 for sale in sales),
    })


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Müşteri bilgileri güncellendi.')
        return redirect('crm-customer-detail', pk=customer.pk)
    return render(request, 'crm/customer_form.html', {'form': form, 'customer': customer})


@login_required
@require_POST
def customer_activity(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = not customer.is_active
    customer.save(update_fields=['is_active'])
    state = 'aktif' if customer.is_active else 'pasif'
    messages.success(request, f'{customer.name} müşterisi {state} duruma alındı.')
    return redirect('crm-customer-detail', pk=customer.pk)


@login_required
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer_name = customer.name
    try:
        customer.delete()
    except ProtectedError:
        messages.error(
            request,
            'Bu müşterinin sipariş geçmişi var. Geçmiş kayıtları korumak için silinemez; müşteriyi pasife alabilirsiniz.',
        )
        return redirect('crm-customer-detail', pk=pk)

    messages.success(request, f'{customer_name} müşterisi ve bağlı CRM satışları silindi.')
    return redirect('crm-list')


@login_required
def sale_list(request):
    selected_status = request.GET.get('status', 'all')
    selected_stage = request.GET.get('stage', 'all')
    query = request.GET.get('q', '').strip()

    sales = Opportunity.objects.select_related('customer')
    if selected_status in Opportunity.Status.values:
        sales = sales.filter(status=selected_status)
    else:
        selected_status = 'all'
    if selected_stage in Opportunity.Stage.values:
        sales = sales.filter(stage=selected_stage)
    else:
        selected_stage = 'all'
    if query:
        sales = sales.filter(Q(title__icontains=query) | Q(customer__name__icontains=query))

    context = {
        'sales': sales.order_by('-updated_at'),
        'query': query,
        'selected_status': selected_status,
        'selected_stage': selected_stage,
        'status_choices': Opportunity.Status.choices,
        'stage_choices': Opportunity.Stage.choices,
        'active_sales': Opportunity.objects.filter(status=Opportunity.Status.ACTIVE).count(),
        'passive_sales': Opportunity.objects.filter(status=Opportunity.Status.PASSIVE).count(),
        'won_sales': Opportunity.objects.filter(status=Opportunity.Status.WON).count(),
    }
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'crm/partials/sale_list_region.html', context)
    return render(request, 'crm/sale_list.html', context)


@login_required
def sale_create(request):
    initial = {}
    customer_id = request.GET.get('customer')
    if customer_id and Customer.objects.filter(pk=customer_id, is_active=True).exists():
        initial['customer'] = customer_id

    form = SaleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        sale = form.save()
        messages.success(request, 'Satış kaydı oluşturuldu.')
        return redirect('crm-customer-detail', pk=sale.customer_id)
    return render(request, 'crm/sale_form.html', {'form': form, 'sale': None})


@login_required
def sale_edit(request, pk):
    sale = get_object_or_404(Opportunity, pk=pk)
    form = SaleForm(request.POST or None, instance=sale)
    if request.method == 'POST' and form.is_valid():
        sale = form.save()
        messages.success(request, 'Satış kaydı güncellendi.')
        return redirect('crm-customer-detail', pk=sale.customer_id)
    return render(request, 'crm/sale_form.html', {'form': form, 'sale': sale})


@login_required
@require_POST
def sale_delete(request, pk):
    sale = get_object_or_404(Opportunity, pk=pk)
    sale.delete()
    messages.success(request, 'Satış kaydı silindi.')
    return redirect('crm-sale-list')


@login_required
@require_POST
def opportunity_advance_view(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk)
    try:
        advance_stage(opportunity)
        messages.success(request, 'Satış bir sonraki aşamaya taşındı.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('crm-sale-list')


@login_required
@require_POST
def opportunity_lose_view(request, pk):
    opportunity = get_object_or_404(Opportunity, pk=pk)
    try:
        mark_as_lost(opportunity)
        messages.success(request, 'Satış kaybedildi olarak kapatıldı.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('crm-sale-list')


@login_required
@require_POST
def sale_activity(request, pk):
    sale = get_object_or_404(Opportunity, pk=pk)
    requested_status = request.POST.get('status')
    try:
        set_sale_activity(sale, requested_status)
        status_label = sale.get_status_display().lower()
        messages.success(request, f'Satış {status_label} duruma alındı.')
    except ValueError as error:
        messages.error(request, str(error))
    return redirect('crm-sale-list')

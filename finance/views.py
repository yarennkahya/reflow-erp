from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from sales.models import Order

from .models import Invoice, Payment
from .services import create_invoice, get_profitability_report, record_payment


@login_required
def report_view(request):
    report = get_profitability_report()
    return render(request, 'finance/list.html', {'report': report})


@login_required
def invoice_list_view(request):
    invoices = Invoice.objects.select_related('order__customer').order_by('-issued_at')
    return render(request, 'finance/invoice_list.html', {'invoices': invoices})


@login_required
def invoice_detail_view(request, pk):
    invoice = get_object_or_404(
        Invoice.objects.select_related('order__customer').prefetch_related('order__items__product', 'payments'),
        pk=pk,
    )

    error = None
    if request.method == 'POST':
        amount_raw = request.POST.get('amount', '').strip()
        method = request.POST.get('method', '').strip()
        try:
            record_payment(invoice, amount_raw, method, user=request.user)
            return redirect('invoice-detail', pk=pk)
        except (ValueError, Exception) as e:
            error = str(e)

    return render(request, 'finance/invoice_detail.html', {
        'invoice': invoice,
        'payment_methods': Payment.Method.choices,
        'error': error,
    })


@login_required
def invoice_create_view(request, order_pk):
    order = get_object_or_404(Order, pk=order_pk)
    if request.method == 'POST':
        try:
            invoice = create_invoice(order)
            messages.success(request, 'Fatura oluşturuldu.')
            return redirect('invoice-detail', pk=invoice.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect('order-detail', pk=order_pk)

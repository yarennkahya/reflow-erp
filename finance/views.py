from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import Invoice, Payment
from .services import get_profitability_report, record_payment


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

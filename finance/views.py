from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from dashboard.grouping import group_by_choice
from dashboard.views_helpers import paginate, pick_view

from sales.models import Order

from .models import Invoice, Payment
from .services import create_invoice, get_profitability_report, record_payment
from .tasks import send_invoice_email_task


@login_required
def report_view(request):
    report = get_profitability_report()
    view = pick_view(request, ('list', 'graph'))

    charts = None
    if view == 'graph':
        # Sipariş bazında gelir/maliyet ve ürün bazında kâr dağılımı.
        by_order = defaultdict(lambda: {'revenue': 0.0, 'cost': 0.0})
        by_product = defaultdict(float)
        for line in report['line_items']:
            bucket = by_order[line['order_id']]
            bucket['revenue'] += line['revenue']
            bucket['cost'] += line['cost']
            by_product[line['product']] += line['profit']

        orders = sorted(by_order.items())[-12:]          # son 12 sipariş
        products = sorted(by_product.items(), key=lambda kv: -kv[1])[:8]

        charts = {
            'profit': {
                'labels': [f'SO #{oid}' for oid, _v in orders],
                'datasets': [
                    {'label': str(_('Gelir')), 'data': [v['revenue'] for _o, v in orders], 'stack': 'a'},
                    {'label': str(_('Maliyet')), 'data': [v['cost'] for _o, v in orders], 'stack': 'a'},
                ],
            },
            'by_product': {
                'labels': [name for name, _p in products],
                'datasets': [{'label': str(_('Kâr')), 'data': [p for _n, p in products]}],
            },
        }

    return render(request, 'finance/list.html', {
        'report': report,
        'view': view,
        'charts': charts,
    })


@login_required
def invoice_list_view(request):
    invoices = Invoice.objects.select_related('order__customer').order_by('-issued_at')
    selected_status = request.GET.get('status', 'all')
    if selected_status in Invoice.Status.values:
        invoices = invoices.filter(status=selected_status)
    else:
        selected_status = 'all'

    rows = list(invoices)
    view = pick_view(request, ('list', 'kanban'))
    page_obj = paginate(request, rows) if view == 'list' else None

    return render(request, 'finance/invoice_list.html', {
        'view': view,
        'view_template': f'finance/_invoices_{view}.html',
        'page_obj': page_obj,
        'invoices': list(page_obj) if page_obj is not None else rows,
        'columns': (
            group_by_choice(
                rows, 'status', Invoice.Status.choices,
                aggregate=lambda inv: float(inv.balance_due),
            ) if view == 'kanban' else None
        ),
        'selected_status': selected_status,
        'status_choices': Invoice.Status.choices,
        'unpaid_count': Invoice.objects.filter(status=Invoice.Status.UNPAID).count(),
        'paid_count': Invoice.objects.filter(status=Invoice.Status.PAID).count(),
    })


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


@login_required
def invoice_preview_view(request, pk):
    """
    Fatura önizlemesi. Satış listesindeki büyüteç bu parçayı bir <dialog>
    içine yükler, bu yüzden tam sayfa değil yalnızca içerik döner.
    """
    invoice = get_object_or_404(
        Invoice.objects
        .select_related('order__customer')
        .prefetch_related('order__items__product', 'payments'),
        pk=pk,
    )
    return render(request, 'finance/_invoice_preview.html', {'invoice': invoice})


def _render_invoice_pdf(invoice):
    from weasyprint import HTML
    html_str = render_to_string('finance/invoice_pdf.html', {'invoice': invoice})
    return HTML(string=html_str).write_pdf()


@login_required
def invoice_pdf_view(request, pk):
    """Faturayı PDF olarak indirir (?preview=1 → tarayıcıda inline açar)."""
    invoice = get_object_or_404(
        Invoice.objects
        .select_related('order__customer')
        .prefetch_related('order__items__product', 'payments'),
        pk=pk,
    )
    pdf = _render_invoice_pdf(invoice)
    filename = f'{invoice.invoice_number}.pdf'
    disposition = 'inline' if request.GET.get('preview') else 'attachment'
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response


@login_required
@require_POST
def invoice_send_view(request, pk):
    """Faturayı müşteriye e-postayla gönderir (Celery görevi olarak kuyruğa alır)."""
    invoice = get_object_or_404(
        Invoice.objects.select_related('order__customer'), pk=pk
    )
    recipient = invoice.order.customer.contact_email
    if not recipient:
        messages.error(
            request,
            f'{invoice.order.customer.name} için e-posta adresi tanımlı değil.',
        )
    else:
        send_invoice_email_task.delay(invoice.pk)
        messages.success(request, f'Fatura #{invoice.pk} → {recipient} adresine gönderiliyor.')
    return redirect(request.POST.get('next') or 'invoice-detail', pk=invoice.pk)

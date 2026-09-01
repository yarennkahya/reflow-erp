from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.translation import gettext as _


@shared_task
def send_invoice_email_task(invoice_id):
    """
    Faturayı PDF ek olarak müşterinin e-posta adresine gönderir.
    Celery ile async çalışır; hata sessizce yutulur.
    """
    from .models import Invoice

    try:
        invoice = (
            Invoice.objects
            .select_related('order__customer')
            .prefetch_related('order__items__product', 'payments')
            .get(pk=invoice_id)
        )
    except Invoice.DoesNotExist:
        return

    recipient = invoice.order.customer.contact_email
    if not recipient:
        return

    body = render_to_string('finance/email/invoice.txt', {
        'invoice': invoice,
        'order': invoice.order,
        'customer': invoice.order.customer,
        'brand': settings.SITE_BRAND,
    })

    try:
        from weasyprint import HTML
        html_str = render_to_string('finance/invoice_pdf.html', {'invoice': invoice})
        pdf_bytes = HTML(string=html_str).write_pdf()
    except Exception:
        pdf_bytes = None

    email = EmailMessage(
        subject=f'{settings.SITE_BRAND} — {_("Fatura")} {invoice.invoice_number}',
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    if pdf_bytes:
        email.attach(f'{invoice.invoice_number}.pdf', pdf_bytes, 'application/pdf')

    try:
        email.send()
    except Exception:
        pass

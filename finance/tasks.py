from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.translation import gettext as _


@shared_task
def send_invoice_email_task(invoice_id):
    """
    Faturayı müşterinin iletişim adresine gönderir.

    notifications.send_notification_email_task ile aynı desen: görev sessizce
    çıkar (fail_silently) — e-posta gönderimi sipariş akışını bloklamamalı.
    """
    from .models import Invoice

    try:
        invoice = (
            Invoice.objects
            .select_related('order__customer')
            .prefetch_related('order__items__product')
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

    send_mail(
        subject=f'{settings.SITE_BRAND} — {_("Fatura")} #{invoice.pk}',
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=True,
    )

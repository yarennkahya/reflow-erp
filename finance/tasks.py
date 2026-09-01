from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _


@shared_task
def send_invoice_email_task(invoice_id):
    """Faturayı PDF ek olarak müşteriye gönderir (kullanıcı tetikler)."""
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


@shared_task
def send_overdue_invoice_reminders():
    """
    Her Pazartesi 09:00 — vadesi geçmiş ve ödenmemiş/kısmen ödenmiş
    faturası olan her müşteriye hatırlatma maili gönderir.
    Aynı müşterinin birden fazla vadesi geçmiş faturası varsa tek mail
    içinde toplu listeler.
    """
    from decimal import Decimal
    from collections import defaultdict
    from .models import Invoice

    today = timezone.now().date()

    # Vadesi geçmiş, hâlâ borcu olan faturalar
    overdue = (
        Invoice.objects
        .select_related('order__customer')
        .prefetch_related('order__items', 'payments')
        .exclude(status=Invoice.Status.PAID)
        .filter(due_date__lt=today)
        .order_by('order__customer__name', 'due_date')
    )

    # Müşteri bazında grupla
    by_customer = defaultdict(list)
    for inv in overdue:
        by_customer[inv.order.customer].append(inv)

    sent = 0
    for customer, invoices in by_customer.items():
        if not customer.contact_email:
            continue

        total_due = sum(inv.balance_due for inv in invoices)

        body = render_to_string('finance/email/invoice_reminder.txt', {
            'customer': customer,
            'invoices': invoices,
            'total_due': total_due,
            'brand': settings.SITE_BRAND,
        })

        try:
            send_mail(
                subject=f'{settings.SITE_BRAND} — Ödeme Hatırlatması ({len(invoices)} fatura)',
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[customer.contact_email],
                fail_silently=True,
            )
            sent += 1
        except Exception:
            pass

    return {'reminders_sent': sent}


@shared_task
def send_weekly_finance_summary():
    """
    Her Pazartesi 09:30 — süper kullanıcılara haftalık finans özeti gönderir.
    Açık fatura sayısı, vadesi geçenler, bu hafta tahsil edilen ödemeler.
    """
    from decimal import Decimal
    from django.contrib.auth.models import User
    from .models import Invoice, Payment

    today = timezone.now().date()
    week_start = today - timezone.timedelta(days=today.weekday() + 7)  # geçen pazartesi
    week_end   = week_start + timezone.timedelta(days=6)

    unpaid_qs  = Invoice.objects.exclude(status=Invoice.Status.PAID)
    overdue_qs = unpaid_qs.filter(due_date__lt=today).select_related('order__customer')
    paid_week  = Payment.objects.filter(paid_at__date__range=(week_start, week_end))

    def sum_balance(qs):
        return sum((inv.balance_due for inv in qs), Decimal('0'))

    context = {
        'week_label': f'{week_start:%d %b} – {week_end:%d %b %Y}',
        'unpaid_count':          unpaid_qs.count(),
        'unpaid_total':          sum_balance(unpaid_qs.prefetch_related('order__items', 'payments')),
        'overdue_count':         overdue_qs.count(),
        'overdue_total':         sum_balance(overdue_qs.prefetch_related('order__items', 'payments')),
        'overdue_invoices':      overdue_qs.prefetch_related('order__items', 'payments'),
        'paid_this_week_count':  paid_week.count(),
        'paid_this_week_total':  sum(p.amount for p in paid_week) if paid_week.exists() else Decimal('0'),
        'partial_count':         Invoice.objects.filter(status=Invoice.Status.PARTIALLY_PAID).count(),
        'brand':                 settings.SITE_BRAND,
    }

    body = render_to_string('finance/email/weekly_summary.txt', context)

    recipients = list(
        User.objects.filter(is_active=True, is_superuser=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )
    if not recipients:
        return {'skipped': 'no superuser emails'}

    try:
        send_mail(
            subject=f'{settings.SITE_BRAND} — Haftalık Finans Özeti ({context["week_label"]})',
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=True,
        )
    except Exception:
        pass

    return {'summary_sent_to': recipients}

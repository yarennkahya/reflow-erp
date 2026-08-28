from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail


@shared_task
def send_notification_email_task(user_id, message):
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    if not user.email:
        return
    send_mail(
        subject='Reflow Coffee ERP - Yeni Bildirim',
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )

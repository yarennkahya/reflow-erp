from django.contrib.auth.models import User

from .models import Notification
from .tasks import send_notification_email_task


def notify_group(group_name, message, url=''):
    """
    Belirtilen RBAC grubundaki tum kullanicilara + tum superuser'lara
    (yonetici her seyi gormeli) bir Notification olusturur ve Celery
    uzerinden e-posta gonderir.
    """
    group_users = User.objects.filter(groups__name=group_name)
    superusers = User.objects.filter(is_superuser=True)
    recipients = (group_users | superusers).distinct()
    for user in recipients:
        Notification.objects.create(recipient=user, message=message, url=url)
        send_notification_email_task.delay(user.id, message)

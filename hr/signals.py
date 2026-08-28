from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import notify_group

from .models import LeaveRequest


@receiver(post_save, sender=LeaveRequest)
def notify_hr_on_leave_request(sender, instance, created, **kwargs):
    if created:
        notify_group(
            'İK Ekibi',
            f'{instance.employee.name} yeni bir izin talebinde bulundu: {instance.leave_type.name}',
            url='/hr/leave/',
        )

from django.db.models.signals import post_save
from django.dispatch import receiver

from notifications.services import notify_group

from .models import ReturnRequest


@receiver(post_save, sender=ReturnRequest)
def notify_sales_on_return_request(sender, instance, created, **kwargs):
    if created:
        notify_group(
            'Satış & CRM Ekibi',
            f'{instance.order_item.product.name} için yeni iade talebi ({instance.get_reason_display()})',
            url='/sales/returns/',
        )

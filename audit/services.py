from django.contrib.contenttypes.models import ContentType

from .models import AuditLog


def log_action(user, action, obj, details=''):
    """
    Herhangi bir modelin herhangi bir kaydi uzerinde yapilan bir islemi
    kaydeder. GenericForeignKey sayesinde tek bir AuditLog tablosu her
    turden kayda (Order, Payment, QualityCheck, GoodsReceipt...) referans
    verebiliyor. user None olabilir (orn. bir yonetim komutundan/sistem
    surecinden cagriliyorsa).
    """
    AuditLog.objects.create(
        user=user,
        action=action,
        content_type=ContentType.objects.get_for_model(obj),
        object_id=obj.pk,
        details=details,
    )

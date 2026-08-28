from celery import shared_task

from .services import scan_defective_return_patterns


@shared_task
def scan_defective_returns():
    return scan_defective_return_patterns()

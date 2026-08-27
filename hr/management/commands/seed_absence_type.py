from django.core.management.base import BaseCommand

from hr.models import LeaveType


class Command(BaseCommand):
    help = 'İzinsiz Devamsızlık leave type oluşturur (idempotent)'

    def handle(self, *args, **options):
        obj, created = LeaveType.objects.get_or_create(
            name='İzinsiz Devamsızlık',
            defaults={'annual_allowance_days': 0},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('LeaveType oluşturuldu: İzinsiz Devamsızlık'))
        else:
            self.stdout.write('LeaveType zaten mevcut: İzinsiz Devamsızlık')

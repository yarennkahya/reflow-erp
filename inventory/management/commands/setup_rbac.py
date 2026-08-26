from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand


GROUP_APP_MAP = {
    'İK Ekibi': ['hr'],
    'Satış & CRM Ekibi': ['sales', 'crm'],
    'Satın Alma Ekibi': ['purchasing'],
    'Üretim & Stok Ekibi': ['production', 'inventory'],
}

DEMO_USERS = {
    'ik_kullanici': 'İK Ekibi',
    'satis_kullanici': 'Satış & CRM Ekibi',
    'satinalma_kullanici': 'Satın Alma Ekibi',
    'uretim_kullanici': 'Üretim & Stok Ekibi',
}

DEMO_PASSWORD = 'Reflow2026!'


class Command(BaseCommand):
    help = (
        'RBAC gruplarini ve izinlerini olusturur, her grup icin '
        'giris yapip test edebilecegin bir demo kullanici acar.'
    )

    def handle(self, *args, **options):
        for group_name, app_labels in GROUP_APP_MAP.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            permissions = Permission.objects.filter(
                content_type__app_label__in=app_labels
            )
            group.permissions.set(permissions)
            self.stdout.write(f'{group_name}: {permissions.count()} izin atandi')

        for username, group_name in DEMO_USERS.items():
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'is_staff': True, 'email': f'{username}@example.com'},
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            user.groups.add(Group.objects.get(name=group_name))
            durum = 'yeni' if created else 'mevcut'
            self.stdout.write(f'{username} -> {group_name} ({durum})')

        self.stdout.write(self.style.SUCCESS('RBAC kurulumu tamamlandi.'))
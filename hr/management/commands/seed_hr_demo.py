from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from hr.models import Department, Employee, Position


DEPARTMENT_POSITIONS = {
    'Üretim': (
        'Üretim Müdürü',
        'Kavurma Uzmanı',
        'Kalite Kontrol Uzmanı',
        'Paketleme Operatörü',
    ),
    'Satış': (
        'Satış Müdürü',
        'Kurumsal Satış Uzmanı',
        'Müşteri Temsilcisi',
    ),
    'Lojistik': (
        'Lojistik Müdürü',
        'Depo Sorumlusu',
        'Sevkiyat Uzmanı',
    ),
    'İnsan Kaynakları': (
        'İnsan Kaynakları Müdürü',
        'İnsan Kaynakları Uzmanı',
    ),
    'Finans': (
        'Finans Müdürü',
        'Muhasebe Uzmanı',
    ),
}

MANAGER_SPECS = (
    ('demo.hr.production.manager@example.test', 'Deniz Aksoy', 'Üretim', 'Üretim Müdürü'),
    ('demo.hr.sales.manager@example.test', 'Selin Arı', 'Satış', 'Satış Müdürü'),
    ('demo.hr.logistics.manager@example.test', 'Okan Yüce', 'Lojistik', 'Lojistik Müdürü'),
    ('demo.hr.people.manager@example.test', 'Derya Erdem', 'İnsan Kaynakları', 'İnsan Kaynakları Müdürü'),
    ('demo.hr.finance.manager@example.test', 'Mert Çelik', 'Finans', 'Finans Müdürü'),
)

ROLE_CYCLE = (
    ('Üretim', 'Kavurma Uzmanı'),
    ('Üretim', 'Kalite Kontrol Uzmanı'),
    ('Üretim', 'Paketleme Operatörü'),
    ('Satış', 'Kurumsal Satış Uzmanı'),
    ('Satış', 'Müşteri Temsilcisi'),
    ('Lojistik', 'Depo Sorumlusu'),
    ('Lojistik', 'Sevkiyat Uzmanı'),
    ('İnsan Kaynakları', 'İnsan Kaynakları Uzmanı'),
    ('Finans', 'Muhasebe Uzmanı'),
)

FIRST_NAMES = (
    'Ada', 'Arda', 'Aslı', 'Berk', 'Ceren', 'Can', 'Defne', 'Ece', 'Emir', 'Eylül',
    'Gizem', 'Hakan', 'İpek', 'Kaan', 'Leyla', 'Mete', 'Naz', 'Onur', 'Pelin', 'Rana',
    'Sarp', 'Tuna', 'Umut', 'Yasemin',
)

LAST_NAMES = (
    'Acar', 'Arslan', 'Başaran', 'Demir', 'Ersoy', 'Güneş', 'Işık', 'Kaya', 'Koç', 'Kurt',
    'Özkan', 'Sarı', 'Şahin', 'Tekin', 'Uysal', 'Yalçın', 'Yıldırım', 'Yılmaz', 'Yücel',
    'Zengin', 'Aydın', 'Bilgin', 'Çolak', 'Durmaz',
)


class Command(BaseCommand):
    help = (
        'Çalışan kartları için idempotent demo personel üretir. Çalışanlar '
        'bulk_create ile ayarlanabilir büyüklükteki chunklar hâlinde eklenir.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=48,
            help='Oluşturulacak demo çalışan sayısı (varsayılan: 48).',
        )
        parser.add_argument(
            '--chunk-size', type=int, default=24,
            help='Her bulk_create çağrısında yazılacak kayıt sayısı (varsayılan: 24).',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Yazma yapmadan kaç kaydın ekleneceğini gösterir.',
        )

    def handle(self, *args, **options):
        count = options['count']
        chunk_size = options['chunk_size']
        dry_run = options['dry_run']

        if count < 0:
            raise CommandError('--count negatif olamaz.')
        if chunk_size < 1:
            raise CommandError('--chunk-size en az 1 olmalıdır.')

        if dry_run:
            existing_emails = set(
                Employee.objects.filter(email__startswith='demo.hr.').values_list('email', flat=True)
            )
            missing_managers = sum(
                email not in existing_emails for email, *_ in MANAGER_SPECS
            )
            missing_employees = sum(
                f'demo.hr.employee.{index:03d}@example.test' not in existing_emails
                for index in range(1, count + 1)
            )
            self.stdout.write(
                f'Önizleme: {missing_managers} yönetici ve {missing_employees} çalışan '
                f'{chunk_size} kayıtlık chunklarla eklenecek.'
            )
            return

        with transaction.atomic():
            positions = self._ensure_organization()
            managers_created = self._ensure_managers(positions, chunk_size)
            employees_created = self._ensure_employees(positions, count, chunk_size)

        self.stdout.write(self.style.SUCCESS(
            f'İK demo verisi hazır: {managers_created} yönetici ve '
            f'{employees_created} çalışan eklendi. '
            f'Chunk boyutu: {chunk_size}.'
        ))

    def _ensure_organization(self):
        positions = {}
        for department_name, titles in DEPARTMENT_POSITIONS.items():
            department, _ = Department.objects.get_or_create(name=department_name)
            for title in titles:
                position, _ = Position.objects.get_or_create(
                    title=title,
                    department=department,
                )
                positions[(department_name, title)] = position
        return positions

    def _ensure_managers(self, positions, chunk_size):
        manager_emails = [email for email, *_ in MANAGER_SPECS]
        existing_emails = set(
            Employee.objects.filter(email__in=manager_emails).values_list('email', flat=True)
        )
        managers_to_create = [
            Employee(
                name=name,
                department=positions[(department_name, title)].department,
                position=positions[(department_name, title)],
                hire_date=date(2020, index + 1, 15),
                email=email,
                phone=f'+90 212 555 0{index + 101}',
            )
            for index, (email, name, department_name, title) in enumerate(MANAGER_SPECS)
            if email not in existing_emails
        ]
        self._bulk_create_in_chunks(managers_to_create, chunk_size)
        return len(managers_to_create)

    def _ensure_employees(self, positions, count, chunk_size):
        manager_by_department = {
            department_name: Employee.objects.get(email=email)
            for email, _name, department_name, _title in MANAGER_SPECS
        }
        employee_emails = [
            f'demo.hr.employee.{index:03d}@example.test'
            for index in range(1, count + 1)
        ]
        existing_emails = set(
            Employee.objects.filter(email__in=employee_emails).values_list('email', flat=True)
        )

        employees_to_create = []
        for index in range(1, count + 1):
            email = f'demo.hr.employee.{index:03d}@example.test'
            if email in existing_emails:
                continue

            department_name, title = ROLE_CYCLE[(index - 1) % len(ROLE_CYCLE)]
            status = Employee.EmploymentStatus.ACTIVE
            if index % 17 == 0:
                status = Employee.EmploymentStatus.TERMINATED
            elif index % 13 == 0:
                status = Employee.EmploymentStatus.ON_LEAVE

            employees_to_create.append(Employee(
                name=(
                    f'{FIRST_NAMES[(index - 1) % len(FIRST_NAMES)]} '
                    f'{LAST_NAMES[((index - 1) // len(FIRST_NAMES)) % len(LAST_NAMES)]}'
                ),
                department=positions[(department_name, title)].department,
                position=positions[(department_name, title)],
                manager=manager_by_department[department_name],
                hire_date=date(2021 + (index % 5), (index % 12) + 1, (index % 27) + 1),
                employment_status=status,
                email=email,
                phone=f'+90 5{index % 100:02d} 555 {index:04d}',
            ))

        self._bulk_create_in_chunks(employees_to_create, chunk_size)
        return len(employees_to_create)

    def _bulk_create_in_chunks(self, employees, chunk_size):
        for start in range(0, len(employees), chunk_size):
            chunk = employees[start:start + chunk_size]
            Employee.objects.bulk_create(chunk, batch_size=chunk_size)
            self.stdout.write(f'  + {len(chunk)} çalışanlık chunk eklendi.')

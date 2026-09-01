from django.db import migrations


IT_POSITIONS = [
    'IT Müdürü',
    'Yazılım Geliştirici',
    'Kıdemli Yazılım Geliştirici',
    'Sistem Yöneticisi',
    'DevOps Mühendisi',
    'Veri Bilimci',
    'IT Destek Uzmanı',
]


def add_it_department(apps, schema_editor):
    Department = apps.get_model('hr', 'Department')
    Position = apps.get_model('hr', 'Position')
    dept, _ = Department.objects.get_or_create(name='IT')
    for title in IT_POSITIONS:
        Position.objects.get_or_create(title=title, department=dept)


def remove_it_department(apps, schema_editor):
    Department = apps.get_model('hr', 'Department')
    Position = apps.get_model('hr', 'Position')
    try:
        dept = Department.objects.get(name='IT')
        Position.objects.filter(department=dept).delete()
        dept.delete()
    except Department.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('hr', '0005_jobopening_closing_date_jobopening_headcount'),
    ]

    operations = [
        migrations.RunPython(add_it_department, remove_it_department),
    ]

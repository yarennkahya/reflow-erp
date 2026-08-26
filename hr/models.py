from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Position(models.Model):
    title = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='positions'
    )

    class Meta:
        ordering = ['title']
        unique_together = ('title', 'department')

    def __str__(self):
        return f'{self.title} ({self.department})'


class Employee(models.Model):
    class EmploymentStatus(models.TextChoices):
        ACTIVE = 'active', 'Aktif'
        ON_LEAVE = 'on_leave', 'İzinde'
        TERMINATED = 'terminated', 'Ayrıldı'

    name = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='employees'
    )
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='employees'
    )
    manager = models.ForeignKey(
        'self', on_delete=models.SET_NULL, related_name='direct_reports',
        null=True, blank=True,
    )
    hire_date = models.DateField()
    employment_status = models.CharField(
        max_length=20, choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


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
        ACTIVE = 'active', _('Aktif')
        ON_LEAVE = 'on_leave', _('İzinde')
        TERMINATED = 'terminated', _('Ayrıldı')

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


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    annual_allowance_days = models.PositiveIntegerField(
        help_text='Bu izin turunden yillik kac gun hakki var.'
    )

    def __str__(self):
        return self.name


class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', _('Beklemede')
        APPROVED = 'approved', _('Onaylandı')
        REJECTED = 'rejected', _('Reddedildi')

    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name='leave_requests'
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        Employee, on_delete=models.SET_NULL, related_name='approved_leaves',
        null=True, blank=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f'{self.employee} - {self.leave_type} ({self.get_status_display()})'



class JobOpening(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', _('Açık')
        CLOSED = 'closed', _('Kapatıldı')
        FILLED = 'filled', _('Dolduruldu')

    title = models.CharField(max_length=255)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name='job_openings'
    )
    position = models.ForeignKey(
        Position, on_delete=models.PROTECT, related_name='job_openings'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    headcount = models.PositiveIntegerField(
        default=1,
        verbose_name='Kontenjan',
        validators=[MinValueValidator(1)],
    )
    closing_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Son Başvuru Tarihi',
    )
    opened_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'


class Candidate(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)
    resume_note = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Application(models.Model):
    class Stage(models.TextChoices):
        APPLIED = 'applied', _('Başvurdu')
        SCREENING = 'screening', _('İnceleniyor')
        INTERVIEW = 'interview', _('Mülakat')
        OFFER = 'offer', _('Teklif')
        HIRED = 'hired', _('İşe Alındı')
        REJECTED = 'rejected', _('Reddedildi')

    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT, related_name='applications'
    )
    job_opening = models.ForeignKey(
        JobOpening, on_delete=models.PROTECT, related_name='applications'
    )
    stage = models.CharField(
        max_length=20, choices=Stage.choices, default=Stage.APPLIED
    )
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.candidate} -> {self.job_opening} ({self.get_stage_display()})'

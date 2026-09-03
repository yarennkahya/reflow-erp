from django.db import models
from django.utils.translation import gettext_lazy as _

from crm.models import Opportunity
from hr.models import Employee
from sales.models import Customer


class Meeting(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', _('Planlandı')
        COMPLETED = 'completed', _('Tamamlandı')
        CANCELLED = 'cancelled', _('İptal Edildi')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    organizer = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name='organized_meetings'
    )
    attendees = models.ManyToManyField(Employee, related_name='meetings', blank=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings'
    )
    opportunity = models.ForeignKey(
        Opportunity, on_delete=models.SET_NULL, null=True, blank=True, related_name='meetings'
    )
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f'{self.title} - {self.start_time:%d %b %Y %H:%M}'

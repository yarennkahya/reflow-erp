from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Application, Candidate, Department, JobOpening, Position


class JobOpeningViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='hr-user', password='secret123'
        )
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='hr'
        ))
        self.department = Department.objects.create(name='İnsan Kaynakları')
        self.position = Position.objects.create(
            title='İşe Alım Uzmanı', department=self.department
        )
        self.client.force_login(self.user)

    def test_job_opening_form_creates_open_position_and_pipeline_summary(self):
        response = self.client.post(reverse('job-opening-create'), {
            'title': 'Kıdemli İşe Alım Uzmanı',
            'department': self.department.pk,
            'position': self.position.pk,
            'headcount': 2,
            'closing_date': (timezone.localdate() + timedelta(days=30)).isoformat(),
        })

        opening = JobOpening.objects.get(title='Kıdemli İşe Alım Uzmanı')
        self.assertRedirects(response, reverse('hr-recruitment'))
        self.assertEqual(opening.status, JobOpening.Status.OPEN)
        self.assertEqual(opening.headcount, 2)

        candidate = Candidate.objects.create(
            name='Test Aday', email='candidate@example.com'
        )
        Application.objects.create(
            candidate=candidate,
            job_opening=opening,
            stage=Application.Stage.HIRED,
        )
        response = self.client.get(reverse('hr-recruitment'))
        self.assertContains(response, 'Pipeline Özeti')
        self.assertContains(response, '1/2')

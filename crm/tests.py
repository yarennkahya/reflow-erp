from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from sales.models import Customer

from .models import Opportunity
from .services import advance_stage, mark_as_lost, set_sale_activity


class OpportunityServiceTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            name='Test Cafe',
            customer_type=Customer.CustomerType.WHOLESALE,
        )

    def create_sale(self):
        return Opportunity.objects.create(
            customer=self.customer,
            title='Aylık kahve tedariki',
        )

    def test_active_sale_advances_through_all_stages_and_is_won(self):
        sale = self.create_sale()

        for expected_stage in (
            Opportunity.Stage.IN_DISCUSSION,
            Opportunity.Stage.PROPOSAL_SENT,
            Opportunity.Stage.NEGOTIATION,
            Opportunity.Stage.WON,
        ):
            advance_stage(sale)
            sale.refresh_from_db()
            self.assertEqual(sale.stage, expected_stage)

        self.assertEqual(sale.status, Opportunity.Status.WON)
        self.assertFalse(sale.is_open)

    def test_passive_sale_cannot_advance_until_reactivated(self):
        sale = self.create_sale()
        set_sale_activity(sale, Opportunity.Status.PASSIVE)

        with self.assertRaises(ValueError):
            advance_stage(sale)

        set_sale_activity(sale, Opportunity.Status.ACTIVE)
        advance_stage(sale)
        sale.refresh_from_db()
        self.assertEqual(sale.stage, Opportunity.Stage.IN_DISCUSSION)

    def test_open_sale_can_be_closed_as_lost(self):
        sale = self.create_sale()

        mark_as_lost(sale)
        sale.refresh_from_db()

        self.assertEqual(sale.stage, Opportunity.Stage.LOST)
        self.assertEqual(sale.status, Opportunity.Status.LOST)
        self.assertFalse(sale.is_open)


class CrmViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='crm-user', password='safe-test-password'
        )
        self.customer = Customer.objects.create(
            name='Mavi Fincan',
            customer_type=Customer.CustomerType.WHOLESALE,
            contact_email='mavi@example.com',
        )
        self.sale = Opportunity.objects.create(
            customer=self.customer,
            title='Kış dönemi tedarik anlaşması',
        )
        self.client.force_login(self.user)

    def test_customer_and_sale_pages_render(self):
        urls = (
            reverse('crm-list'),
            reverse('crm-customer-detail', args=[self.customer.pk]),
            reverse('crm-customer-edit', args=[self.customer.pk]),
            reverse('crm-sale-list'),
            reverse('crm-sale-create'),
            reverse('crm-sale-edit', args=[self.sale.pk]),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_customer_and_sale_can_be_created_from_crm(self):
        response = self.client.post(reverse('crm-customer-create'), {
            'name': 'Yeni Müşteri',
            'customer_type': Customer.CustomerType.RETAIL,
            'contact_email': 'yeni@example.com',
            'contact_phone': '555 000 00 00',
        })
        self.assertRedirects(
            response,
            reverse('crm-customer-detail', args=[Customer.objects.get(name='Yeni Müşteri').pk]),
        )

        response = self.client.post(reverse('crm-sale-create'), {
            'customer': self.customer.pk,
            'title': 'Yeni CRM satışı',
            'status': Opportunity.Status.PASSIVE,
            'stage': Opportunity.Stage.NEW,
            'estimated_value': '2500.00',
            'notes': 'İlk teklif için beklemede.',
        })
        self.assertRedirects(
            response,
            reverse('crm-customer-detail', args=[self.customer.pk]),
        )
        self.assertTrue(
            Opportunity.objects.filter(
                customer=self.customer,
                title='Yeni CRM satışı',
                status=Opportunity.Status.PASSIVE,
            ).exists()
        )

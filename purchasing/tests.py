from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from inventory.models import Business
from purchasing.models import PurchaseOrder


class PurchasingViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='secret123',
            is_staff=True,
            is_superuser=True,
        )
        self.supplier = Business.objects.create(
            name='Brazil Farms Co',
            business_type='supplier',
            contact_email='supplier@example.com',
            contact_phone='+1555',
        )
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status='received',
        )

    def test_purchase_list_has_clickable_po_link_and_no_cache_headers(self):
        self.client.force_login(self.user)
        response = self.client.get('/purchasing/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers.get('Cache-Control', '').lower())
        self.assertIn('PO #', response.content.decode())
        self.assertIn(f'href="/purchasing/orders/{self.po.pk}/"', response.content.decode())

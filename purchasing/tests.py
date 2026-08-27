from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from inventory.models import Business, Product

from .models import PurchaseOrder, PurchaseOrderItem
from .services import advance_order_status, receive_goods


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
            business_type=Business.BusinessType.SUPPLIER,
            contact_email='supplier@example.com',
            contact_phone='+1555',
        )
        self.product = Product.objects.create(
            name='Brazil Santos Green',
            category='Yeşil kahve',
            unit=Product.Unit.KILOGRAM,
            business=self.supplier,
        )
        self.po = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status=PurchaseOrder.Status.RECEIVED,
        )
        self.client.force_login(self.user)

    def test_purchase_list_has_clickable_po_link_and_no_cache_headers(self):
        response = self.client.get(reverse('purchasing-list'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('no-store', response.headers.get('Cache-Control', '').lower())
        self.assertIn('PO #', response.content.decode())
        self.assertIn(
            f'href="/purchasing/orders/{self.po.pk}/"',
            response.content.decode(),
        )

    def test_supplier_and_purchase_pages_render(self):
        urls = (
            reverse('supplier-list'),
            reverse('supplier-detail', args=[self.supplier.pk]),
            reverse('supplier-edit', args=[self.supplier.pk]),
            reverse('supplier-product-create', args=[self.supplier.pk]),
            reverse('purchase-order-create'),
            reverse('purchase-order-detail', args=[self.po.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_order_can_be_created_with_item_and_advanced(self):
        response = self.client.post(reverse('purchase-order-create'), {
            'supplier': self.supplier.pk,
            'expected_delivery_date': timezone.localdate() + timedelta(days=4),
            'notes': 'Haftalık tedarik siparişi',
        })
        order = PurchaseOrder.objects.exclude(pk=self.po.pk).get()
        self.assertRedirects(response, reverse('purchase-order-detail', args=[order.pk]))
        self.assertEqual(order.status, PurchaseOrder.Status.DRAFT)

        response = self.client.post(
            reverse('purchase-order-item-create', args=[order.pk]),
            {
                'product': self.product.pk,
                'quantity_ordered': '25.000',
                'unit_price': '42.50',
            },
        )
        self.assertRedirects(response, reverse('purchase-order-detail', args=[order.pk]))
        self.assertEqual(order.items.count(), 1)

        response = self.client.post(reverse('purchase-order-advance', args=[order.pk]))
        self.assertRedirects(response, reverse('purchase-order-detail', args=[order.pk]))
        order.refresh_from_db()
        self.assertEqual(order.status, PurchaseOrder.Status.SENT)


class PurchasingServiceTests(TestCase):
    def setUp(self):
        self.supplier = Business.objects.create(
            name='Test Supplier',
            business_type=Business.BusinessType.SUPPLIER,
            contact_email='test-supplier@example.com',
            contact_phone='+90 555 000 00 00',
        )
        self.product = Product.objects.create(
            name='Test Green Coffee',
            category='Yeşil kahve',
            unit=Product.Unit.KILOGRAM,
            business=self.supplier,
        )

    def test_empty_draft_cannot_be_sent(self):
        order = PurchaseOrder.objects.create(supplier=self.supplier)

        with self.assertRaises(ValueError):
            advance_order_status(order)

    def test_receiving_all_quantity_marks_order_as_received(self):
        order = PurchaseOrder.objects.create(
            supplier=self.supplier,
            status=PurchaseOrder.Status.SENT,
        )
        item = PurchaseOrderItem.objects.create(
            purchase_order=order,
            product=self.product,
            quantity_ordered=Decimal('20.000'),
            unit_price=Decimal('44.50'),
        )

        receipt = receive_goods(
            item,
            quantity_received=Decimal('20.000'),
            lot_code='TEST-PO-LOT-001',
            expiry_date=timezone.localdate() + timedelta(days=90),
        )

        order.refresh_from_db()
        self.assertEqual(receipt.lot.unit_cost, Decimal('44.50'))
        self.assertEqual(order.status, PurchaseOrder.Status.RECEIVED)

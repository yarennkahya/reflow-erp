from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Business, Lot, MovementType, Product, StockMovement, Warehouse
from .services import get_freshness_status, get_stock_summary


class InventoryViewsTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username='inventory-user',
            password='secret123',
        )
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='inventory'
        ))
        self.supplier = Business.objects.create(
            name='Inventory Test Supplier',
            business_type=Business.BusinessType.SUPPLIER,
            contact_email='inventory-supplier@example.com',
            contact_phone='+90 555 000 00 01',
        )
        self.product = Product.objects.create(
            name='Inventory Test Coffee',
            category='Yeşil kahve',
            unit=Product.Unit.KILOGRAM,
            business=self.supplier,
        )
        self.warehouse = Warehouse.objects.create(
            name='Test Ana Depo', city='İstanbul'
        )
        self.lot = Lot.objects.create(
            product=self.product,
            warehouse=self.warehouse,
            lot_code='INV-TEST-001',
            expiry_date=timezone.localdate() + timedelta(days=30),
            quantity_received=Decimal('10.000'),
            unit_cost=Decimal('92.50'),
        )
        StockMovement.objects.create(
            lot=self.lot,
            movement_type=MovementType.OUT_SALE,
            quantity=Decimal('-3.000'),
        )
        self.client.force_login(self.user)

    def test_stock_list_uses_calculated_remaining_quantity(self):
        response = self.client.get(reverse('inventory-list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Inventory Test Coffee')
        self.assertContains(response, '7.000 Kg')
        self.assertContains(response, reverse('lot-detail', args=[self.lot.pk]))

    def test_lot_and_warehouse_detail_pages_render(self):
        urls = (
            reverse('lot-detail', args=[self.lot.pk]),
            reverse('warehouse-list'),
            reverse('warehouse-detail', args=[self.warehouse.pk]),
            reverse('warehouse-edit', args=[self.warehouse.pk]),
        )

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_warehouse_can_be_created_and_lotted_warehouse_cannot_be_deleted(self):
        response = self.client.post(reverse('warehouse-create'), {
            'name': 'İzmir Transfer Deposu',
            'city': 'İzmir',
        })
        created_warehouse = Warehouse.objects.get(name='İzmir Transfer Deposu')
        self.assertRedirects(
            response, reverse('warehouse-detail', args=[created_warehouse.pk])
        )

        response = self.client.post(
            reverse('warehouse-activity', args=[self.warehouse.pk])
        )
        self.assertRedirects(response, reverse('warehouse-detail', args=[self.warehouse.pk]))
        self.warehouse.refresh_from_db()
        self.assertFalse(self.warehouse.is_active)

        response = self.client.post(
            reverse('warehouse-delete', args=[self.warehouse.pk])
        )
        self.assertRedirects(response, reverse('warehouse-detail', args=[self.warehouse.pk]))
        self.assertTrue(Warehouse.objects.filter(pk=self.warehouse.pk).exists())


class InventoryServiceTests(TestCase):
    def setUp(self):
        supplier = Business.objects.create(
            name='Service Test Supplier',
            business_type=Business.BusinessType.SUPPLIER,
            contact_email='service-supplier@example.com',
            contact_phone='+90 555 000 00 02',
        )
        self.product = Product.objects.create(
            name='Service Test Coffee',
            category='Yeşil kahve',
            unit=Product.Unit.KILOGRAM,
            business=supplier,
        )
        self.lot = Lot.objects.create(
            product=self.product,
            lot_code='INV-SERVICE-001',
            expiry_date=timezone.localdate() + timedelta(days=2),
            quantity_received=Decimal('4.000'),
        )

    def test_freshness_and_stock_summary_include_remaining_stock(self):
        StockMovement.objects.create(
            lot=self.lot,
            movement_type=MovementType.OUT_PRODUCTION,
            quantity=Decimal('-1.250'),
        )

        self.assertEqual(get_freshness_status(self.lot), 'PRIORITY_SALE')
        summary = get_stock_summary('Service Test')
        self.assertEqual(summary['product'], self.product.name)
        self.assertEqual(summary['total_remaining'], 2.75)
        self.assertEqual(summary['lots'][0]['freshness_status'], 'PRIORITY_SALE')


class ModuleAccessTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='purchasing-role-user', password='secret123'
        )
        self.user.user_permissions.add(*Permission.objects.filter(
            content_type__app_label='purchasing'
        ))
        self.client.force_login(self.user)

    def test_role_can_open_its_module_but_is_redirected_from_others(self):
        response = self.client.get(reverse('purchasing-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'is-locked')

        self.assertEqual(self.client.get(reverse('chat-page')).status_code, 200)

        response = self.client.get(reverse('hr-list'))
        self.assertRedirects(response, reverse('dashboard-home'))
